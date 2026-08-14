"""Fail-closed HTTPS CONNECT gateway for approved Provider hosts.

This is intentionally not a general forward proxy. It accepts CONNECT to port
443 only, resolves and pins a public address, and asks the internal API to
atomically consume the opaque one-use invocation grant before opening a tunnel.
It never accepts Provider credentials and never logs request bodies or grants.
"""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import hmac
import ipaddress
import json
import os
import selectors
import socket
import socketserver
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_HEADER_BYTES = 16 * 1024
CONNECT_TIMEOUT_SECONDS = 10
IDLE_TIMEOUT_SECONDS = 60


class Denied(Exception):
    """A stable, non-sensitive denial reason."""


@dataclass(frozen=True)
class GateState:
    domains: frozenset[str]
    allowlist_sha256: str


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_timestamp(value: Any) -> dt.datetime:
    if not isinstance(value, str):
        raise Denied("GATE_EXPIRY_MISSING")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Denied("GATE_EXPIRY_INVALID") from exc
    if parsed.tzinfo is None:
        raise Denied("GATE_EXPIRY_INVALID")
    return parsed.astimezone(dt.timezone.utc)


def load_gate_state() -> GateState:
    gate_path = Path(os.environ.get("BIAICE_EGRESS_GATE_FILE", ""))
    allowlist_path = Path(os.environ.get("BIAICE_EGRESS_ALLOWLIST_FILE", ""))
    verification_key_path = Path(
        os.environ.get("BIAICE_EGRESS_GATE_VERIFICATION_KEY_FILE", "")
    )
    if (
        not gate_path.is_file()
        or not allowlist_path.is_file()
        or not verification_key_path.is_file()
    ):
        raise Denied("BYOK_GATE_EVIDENCE_MISSING")

    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Denied("BYOK_GATE_EVIDENCE_INVALID") from exc

    if gate.get("gate") != "BYOK_SECRET_GATE":
        raise Denied("BYOK_GATE_NAME_INVALID")
    if gate.get("status") != "PASS" or gate.get("validity_state") != "CURRENT":
        raise Denied("BYOK_GATE_NOT_CURRENT_PASS")
    if _parse_timestamp(gate.get("expires_at")) <= _utc_now():
        raise Denied("BYOK_GATE_STALE")
    if not isinstance(gate.get("assessment_id"), str) or not gate["assessment_id"]:
        raise Denied("BYOK_GATE_ASSESSMENT_MISSING")
    signature = gate.get("evidence_signature")
    if not isinstance(signature, str) or not signature.startswith("hmac-sha256:"):
        raise Denied("BYOK_GATE_SIGNATURE_MISSING")
    try:
        verification_key = verification_key_path.read_bytes().strip()
    except OSError as exc:
        raise Denied("BYOK_GATE_VERIFIER_UNAVAILABLE") from exc
    if len(verification_key) < 32:
        raise Denied("BYOK_GATE_VERIFIER_INVALID")
    canonical_gate = {
        key: value for key, value in gate.items() if key != "evidence_signature"
    }
    expected_signature = hmac.new(
        verification_key,
        json.dumps(
            canonical_gate,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature.removeprefix("hmac-sha256:"), expected_signature):
        raise Denied("BYOK_GATE_SIGNATURE_INVALID")

    raw_domains = allowlist_path.read_text(encoding="ascii")
    domains: set[str] = set()
    for raw_line in raw_domains.splitlines():
        value = raw_line.partition("#")[0].strip().rstrip(".").lower()
        if not value:
            continue
        if any(token in value for token in ("://", "/", "*", ":")):
            raise Denied("PROVIDER_ALLOWLIST_ENTRY_INVALID")
        try:
            ipaddress.ip_address(value)
        except ValueError:
            pass
        else:
            raise Denied("PROVIDER_ALLOWLIST_IP_LITERAL")
        try:
            ascii_domain = value.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise Denied("PROVIDER_ALLOWLIST_ENTRY_INVALID") from exc
        if "." not in ascii_domain:
            raise Denied("PROVIDER_ALLOWLIST_ENTRY_INVALID")
        domains.add(ascii_domain)

    if not domains:
        raise Denied("PROVIDER_ALLOWLIST_EMPTY")
    canonical = "".join(f"{domain}\n" for domain in sorted(domains)).encode("ascii")
    digest = hashlib.sha256(canonical).hexdigest()
    if gate.get("catalog_allowlist_sha256") != digest:
        raise Denied("PROVIDER_CATALOG_HASH_MISMATCH")
    return GateState(frozenset(domains), digest)


def validate_target(host: str, port: int, gate: GateState) -> tuple[int, tuple[Any, ...]]:
    normalized = host.rstrip(".").lower()
    try:
        normalized = normalized.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise Denied("PROVIDER_HOST_INVALID") from exc
    if port != 443:
        raise Denied("PROVIDER_PORT_DENIED")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        pass
    else:
        raise Denied("PROVIDER_IP_LITERAL_DENIED")
    if normalized not in gate.domains:
        raise Denied("PROVIDER_HOST_NOT_APPROVED")

    try:
        resolved = socket.getaddrinfo(normalized, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise Denied("PROVIDER_DNS_FAILED") from exc
    if not resolved:
        raise Denied("PROVIDER_DNS_FAILED")

    candidates: list[tuple[int, tuple[Any, ...]]] = []
    for family, socktype, proto, _canonname, sockaddr in resolved:
        address = ipaddress.ip_address(sockaddr[0])
        if (
            not address.is_global
            or address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise Denied("PROVIDER_DNS_PRIVATE_OR_RESERVED")
        if socktype == socket.SOCK_STREAM and proto in (0, socket.IPPROTO_TCP):
            candidates.append((family, sockaddr))
    if not candidates:
        raise Denied("PROVIDER_DNS_NO_PUBLIC_ADDRESS")
    # The exact sockaddr is returned and used for connect: no second DNS lookup.
    return candidates[0]


def consume_authorization(grant: str, host: str, gate: GateState) -> None:
    if not grant or len(grant) > 4096:
        raise Denied("EGRESS_GRANT_MISSING")
    endpoint = os.environ.get("BIAICE_EGRESS_AUTHORIZATION_URL", "")
    parsed_endpoint = urllib.parse.urlsplit(endpoint)
    if (
        parsed_endpoint.scheme != "http"
        or parsed_endpoint.hostname != "api"
        or parsed_endpoint.port != 8000
        or parsed_endpoint.path != "/internal/provider-egress/authorize"
        or parsed_endpoint.query
        or parsed_endpoint.fragment
    ):
        raise Denied("EGRESS_AUTHORIZER_INVALID")
    payload = json.dumps(
        {
            "grant": grant,
            "target_host": host,
            "target_port": 443,
            "catalog_allowlist_sha256": gate.allowlist_sha256,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
            return None

    try:
        opener = urllib.request.build_opener(NoRedirect)
        with opener.open(request, timeout=5) as response:
            body = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise Denied("EGRESS_AUTHORIZER_UNAVAILABLE") from exc
    if response.status != 200 or body.get("authorized") is not True:
        raise Denied("EGRESS_GRANT_DENIED")
    if body.get("target_host") != host or body.get("single_use_consumed") is not True:
        raise Denied("EGRESS_GRANT_BINDING_MISMATCH")
    if _parse_timestamp(body.get("expires_at")) <= _utc_now():
        raise Denied("EGRESS_GRANT_EXPIRED")


class RateLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = max(1, min(limit, 600))
        self.events: dict[str, collections.deque[float]] = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        cutoff = time.monotonic() - 60
        with self.lock:
            queue = self.events.setdefault(key, collections.deque())
            while queue and queue[0] < cutoff:
                queue.popleft()
            if len(queue) >= self.limit:
                return False
            queue.append(time.monotonic())
            return True


RATE_LIMITER = RateLimiter(int(os.environ.get("BIAICE_EGRESS_MAX_CONNECTIONS_PER_MINUTE", "30")))


def audit(outcome: str, client: str, host: str | None = None, reason: str | None = None) -> None:
    event = {
        "timestamp": _utc_now().isoformat(),
        "component": "provider-egress-gateway",
        "outcome": outcome,
        "client": client,
    }
    if host:
        event["target_host"] = host
    if reason:
        event["reason_code"] = reason
    print(json.dumps(event, separators=(",", ":"), sort_keys=True), flush=True)


class ProxyHandler(socketserver.BaseRequestHandler):
    def _send(self, status: int, message: str) -> None:
        self.request.sendall(
            f"HTTP/1.1 {status} {message}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n".encode("ascii")
        )

    def handle(self) -> None:
        client = self.client_address[0]
        target_host: str | None = None
        try:
            self.request.settimeout(10)
            header = bytearray()
            while b"\r\n\r\n" not in header:
                chunk = self.request.recv(2048)
                if not chunk:
                    raise Denied("PROXY_REQUEST_INCOMPLETE")
                header.extend(chunk)
                if len(header) > MAX_HEADER_BYTES:
                    raise Denied("PROXY_HEADERS_TOO_LARGE")
            head, _separator, remainder = bytes(header).partition(b"\r\n\r\n")
            lines = head.decode("iso-8859-1").split("\r\n")

            if lines[0] == "GET /health HTTP/1.1":
                load_gate_state()
                body = b'{"status":"ok"}'
                self.request.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 15\r\nConnection: close\r\n\r\n"
                    + body
                )
                return

            parts = lines[0].split(" ")
            if len(parts) != 3 or parts[0] != "CONNECT" or parts[2] != "HTTP/1.1":
                raise Denied("HTTPS_CONNECT_REQUIRED")
            authority = parts[1]
            if authority.count(":") != 1:
                raise Denied("PROVIDER_AUTHORITY_INVALID")
            target_host, raw_port = authority.rsplit(":", 1)
            try:
                target_port = int(raw_port)
            except ValueError as exc:
                raise Denied("PROVIDER_PORT_INVALID") from exc

            headers: dict[str, str] = {}
            for line in lines[1:]:
                name, separator, value = line.partition(":")
                if not separator:
                    raise Denied("PROXY_HEADER_INVALID")
                headers[name.strip().lower()] = value.strip()
            authorization = headers.get("proxy-authorization", "")
            scheme, separator, grant = authorization.partition(" ")
            if not separator or scheme != "Biaice":
                raise Denied("EGRESS_GRANT_MISSING")
            if remainder:
                raise Denied("CONNECT_EARLY_DATA_DENIED")
            if not RATE_LIMITER.allow(client):
                raise Denied("EGRESS_RATE_LIMITED")

            gate = load_gate_state()
            family, sockaddr = validate_target(target_host, target_port, gate)
            consume_authorization(grant, target_host, gate)

            upstream = socket.socket(family, socket.SOCK_STREAM)
            try:
                upstream.settimeout(CONNECT_TIMEOUT_SECONDS)
                upstream.connect(sockaddr)
                upstream.settimeout(IDLE_TIMEOUT_SECONDS)
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                self.request.settimeout(IDLE_TIMEOUT_SECONDS)
                self._tunnel(upstream)
            finally:
                upstream.close()
            audit("ALLOWED", client, target_host)
        except Denied as exc:
            self._send(403, "Forbidden")
            audit("BLOCKED", client, target_host, str(exc))
        except (OSError, TimeoutError):
            try:
                self._send(502, "Bad Gateway")
            except OSError:
                pass
            audit("FAILED", client, target_host, "UPSTREAM_CONNECTION_FAILED")

    def _tunnel(self, upstream: socket.socket) -> None:
        selector = selectors.DefaultSelector()
        selector.register(self.request, selectors.EVENT_READ, upstream)
        selector.register(upstream, selectors.EVENT_READ, self.request)
        last_activity = time.monotonic()
        while time.monotonic() - last_activity < IDLE_TIMEOUT_SECONDS:
            events = selector.select(timeout=1)
            for key, _mask in events:
                source: socket.socket = key.fileobj
                destination: socket.socket = key.data
                data = source.recv(64 * 1024)
                if not data:
                    return
                destination.sendall(data)
                last_activity = time.monotonic()


class ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    # Startup is blocked unless Gate evidence is current and its hash matches a
    # non-empty exact-host allowlist. It is rechecked for every connection.
    try:
        gate = load_gate_state()
    except Denied as exc:
        audit("STARTUP_BLOCKED", "local", reason=str(exc))
        raise SystemExit(78) from exc
    host, raw_port = os.environ.get("BIAICE_EGRESS_LISTEN", "0.0.0.0:8888").rsplit(":", 1)
    audit("STARTED", "local", reason=f"allowlist_sha256:{gate.allowlist_sha256}")
    with ThreadingServer((host, int(raw_port)), ProxyHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
