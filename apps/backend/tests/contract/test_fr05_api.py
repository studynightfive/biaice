"""Contract and lifecycle tests for the FR-05 market API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from conftest import DOMAIN_A, TENANT_A, TENANT_B, StaticAuthenticator
from fastapi.testclient import TestClient

from biaice.api.operation_catalog import OPERATION_CATALOG
from biaice.core.audit import HashChainAuditWriter, InMemoryAppendOnlyAuditSink
from biaice.core.auth import IdentityContext, Role, TenantScope
from biaice.core.config import Settings
from biaice.main import create_app

NOW = datetime.now(timezone.utc)
AUTHORIZATION = {"Authorization": "Bearer fr05-contract-token"}


def _identity(
    *,
    tenant_id: UUID = TENANT_A,
    all_decision_units: bool = True,
    decision_unit_ids: frozenset[UUID] = frozenset(),
) -> IdentityContext:
    return IdentityContext(
        subject_id=uuid4(),
        username="fr05-legal-reviewer",
        roles=frozenset({Role.LEGAL_PRIVACY}),
        scope=TenantScope(
            tenant_id=tenant_id,
            data_domain_id=DOMAIN_A,
            all_decision_units=all_decision_units,
            decision_unit_ids=decision_unit_ids,
        ),
        mfa_verified=True,
        authenticated_at=NOW,
    )


def _app(identity: IdentityContext | None = None):
    identity = identity or _identity()
    sink = InMemoryAppendOnlyAuditSink()
    authenticator = StaticAuthenticator(identity)
    app = create_app(
        settings=Settings(environment="test"),
        authenticator=authenticator,
        audit_writer=HashChainAuditWriter(sink),
    )
    return app, authenticator, sink


def _client() -> TestClient:
    app, _, _ = _app()
    client = TestClient(app)
    client.headers.update(AUTHORIZATION)
    return client


def _headers(key: str) -> dict[str, str]:
    return {"Idempotency-Key": f"fr05-{key}-00000001"}


def _create_competitor(client: TestClient, *, key: str = "create-competitor") -> dict:
    response = client.post(
        "/api/v1/competitors",
        headers=_headers(key),
        json={
            "legal_name": "Example Bidder Ltd",
            "canonical_subject_key": "Example Bidder",
            "aliases": ["Example Bidder"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _source_body() -> dict:
    return {
        "source_uri": "https://registry.example/evidence/1",
        "source_type": "PUBLIC_REGISTRY",
        "purpose": "COMPETITOR_ANALYSIS",
        "legal_basis_ref": "legitimate-interest-2026",
        "retention_expires_at": (NOW + timedelta(days=30)).isoformat(),
        "data_classification": "PUBLIC",
        "evidence_refs": ["registry-record-1"],
        "notes": "synthetic contract fixture",
    }


def _profile_body(source_id: str) -> dict:
    return {
        "source_ids": [source_id],
        "participation_assumptions": {"participates": 0.6},
        "bid_assumptions": {"relative_price": 0.95},
        "potential_response_states": ["RESPONSIVE", "NON_RESPONSIVE"],
        "subjective_variables": {"service_quality": 0.7},
        "validity_assumptions": ["public registry remains current"],
        "coverage_notes": "bounded public evidence",
        "bias_notes": "registry reporting bias",
        "drift_notes": "review monthly",
        "data_quality": "reviewed-public-source",
    }


def test_all_25_fr05_operations_are_typed_and_implemented() -> None:
    schema = create_app(settings=Settings(environment="contract")).openapi()
    operations = {
        operation["operationId"]: operation
        for path_item in schema["paths"].values()
        for operation in path_item.values()
        if isinstance(operation, dict) and operation.get("x-fr") == "FR-05"
    }
    expected = {
        operation.operation_id for operation in OPERATION_CATALOG if operation.fr == "FR-05"
    }

    assert len(expected) == 25
    assert set(operations) == expected
    assert all(operation["x-contract-only"] is False for operation in operations.values())
    assert all(
        "contract-only" not in operation.get("tags", []) for operation in operations.values()
    )

    create_schema = operations["create_competitor"]["requestBody"]["content"]["application/json"][
        "schema"
    ]
    response_schema = operations["create_competitor"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert create_schema["$ref"].endswith("/CreateCompetitorRequest")
    assert response_schema["$ref"].endswith("/Competitor")


def test_competitor_source_profile_lifecycle_and_etag() -> None:
    app, _, sink = _app()
    with TestClient(app) as client:
        client.headers.update(AUTHORIZATION)
        assert client.get("/api/v1/competitors").json() == {"items": []}

        missing_idempotency = client.post(
            "/api/v1/competitors",
            json={
                "legal_name": "Example Bidder Ltd",
                "canonical_subject_key": "example-bidder",
            },
        )
        assert missing_idempotency.status_code == 400
        assert missing_idempotency.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"

        create_body = {
            "legal_name": "Example Bidder Ltd",
            "canonical_subject_key": " Example Bidder ",
            "aliases": ["Example Bidder"],
        }
        created_response = client.post(
            "/api/v1/competitors",
            headers=_headers("competitor-create"),
            json=create_body,
        )
        assert created_response.status_code == 200, created_response.text
        competitor = created_response.json()
        competitor_id = competitor["competitor_id"]
        assert competitor["canonical_subject_key"] == "examplebidder"
        etag = created_response.headers["etag"]

        replay = client.post(
            "/api/v1/competitors",
            headers=_headers("competitor-create"),
            json=create_body,
        )
        assert replay.status_code == 200
        assert replay.json() == competitor
        idempotency_conflict = client.post(
            "/api/v1/competitors",
            headers=_headers("competitor-create"),
            json={**create_body, "legal_name": "Conflicting Bidder Ltd"},
        )
        assert idempotency_conflict.status_code == 409
        assert idempotency_conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"

        duplicate = client.post(
            "/api/v1/competitors",
            headers=_headers("competitor-duplicate"),
            json={
                "legal_name": "Example Bidder Alias",
                "canonical_subject_key": "examplebidder",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "IDEMPOTENCY_CONFLICT"

        fetched = client.get(f"/api/v1/competitors/{competitor_id}")
        assert fetched.status_code == 200
        assert fetched.headers["etag"] == etag
        assert (
            client.get("/api/v1/competitors").json()["items"][0]["competitor_id"] == competitor_id
        )

        missing_if_match = client.patch(
            f"/api/v1/competitors/{competitor_id}",
            json={"legal_name": "Updated Bidder Ltd"},
        )
        assert missing_if_match.status_code == 428
        assert missing_if_match.json()["code"] == "IF_MATCH_REQUIRED"

        mismatch = client.patch(
            f"/api/v1/competitors/{competitor_id}",
            headers={"If-Match": f'"{"0" * 64}"'},
            json={"legal_name": "Updated Bidder Ltd"},
        )
        assert mismatch.status_code == 412
        assert mismatch.json()["code"] == "ETAG_MISMATCH"

        updated = client.patch(
            f"/api/v1/competitors/{competitor_id}",
            headers={"If-Match": etag},
            json={"legal_name": "Updated Bidder Ltd"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["legal_name"] == "Updated Bidder Ltd"
        assert updated.headers["etag"] != etag

        source_response = client.post(
            f"/api/v1/competitors/{competitor_id}/sources",
            headers=_headers("source-create"),
            json=_source_body(),
        )
        assert source_response.status_code == 200, source_response.text
        source = source_response.json()
        source_id = source["source_id"]
        assert source["review_state"] == "DRAFT"
        assert client.get(f"/api/v1/competitor-sources/{source_id}").status_code == 200
        assert (
            client.get(f"/api/v1/competitors/{competitor_id}/sources").json()["items"][0][
                "source_id"
            ]
            == source_id
        )

        blocked_profile = client.post(
            f"/api/v1/competitors/{competitor_id}/profiles/build",
            headers=_headers("profile-blocked"),
            json=_profile_body(source_id),
        )
        assert blocked_profile.status_code == 503
        assert blocked_profile.json()["code"] == "GATE_NOT_CURRENT"

        reviewed = client.post(
            f"/api/v1/competitor-sources/{source_id}/review",
            headers=_headers("source-review"),
            json={},
        )
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["review_state"] == "REVIEWED"
        assert reviewed.json()["subject_resolved"] is True

        profile_response = client.post(
            f"/api/v1/competitors/{competitor_id}/profiles/build",
            headers=_headers("profile-build"),
            json=_profile_body(source_id),
        )
        assert profile_response.status_code == 200, profile_response.text
        profile = profile_response.json()
        profile_id = profile["profile_id"]
        assert profile["state"] == "DRAFT"
        assert client.get(f"/api/v1/competitor-profiles/{profile_id}").status_code == 200
        assert (
            client.get(f"/api/v1/competitors/{competitor_id}/profiles").json()["items"][0][
                "profile_id"
            ]
            == profile_id
        )

        published = client.post(
            f"/api/v1/competitor-profiles/{profile_id}/publish",
            headers=_headers("profile-publish"),
            json={"reason_code": "REVIEW_COMPLETE"},
        )
        assert published.status_code == 200, published.text
        assert published.json()["state"] == "PUBLISHED"

        quarantined = client.post(
            f"/api/v1/competitor-sources/{source_id}/quarantine",
            headers=_headers("source-quarantine"),
            json={"reason": "source integrity changed"},
        )
        assert quarantined.status_code == 200, quarantined.text
        assert quarantined.json()["review_state"] == "QUARANTINED"
        assert client.get(f"/api/v1/competitor-profiles/{profile_id}").json()["state"] == (
            "QUARANTINED"
        )

        archived = client.post(
            f"/api/v1/competitors/{competitor_id}/archive",
            headers=_headers("competitor-archive"),
            json={"reason": "no longer relevant"},
        )
        assert archived.status_code == 200, archived.text
        assert archived.json()["archived_at"] is not None

    audit_actions = {event.action for event in sink.list_events(_identity().scope)}
    assert {
        "market.competitor.create",
        "market.competitor.update_draft",
        "market.competitor_source.create",
        "market.competitor_source.review",
        "market.competitor_profile.build",
        "market.competitor_profile.publish",
        "market.competitor_source.quarantine",
        "market.competitor.archive",
    }.issubset(audit_actions)


def test_market_prior_requires_review_before_publish() -> None:
    unit_id = uuid4()
    with _client() as client:
        assert client.get(f"/api/v1/decision-units/{unit_id}/market-priors").json() == {"items": []}
        created = client.post(
            f"/api/v1/decision-units/{unit_id}/market-priors",
            headers=_headers("prior-create"),
            json={
                "evidence_refs": ["market-survey-2026"],
                "purpose": "MARKET_SCENARIO",
                "legal_basis_ref": "public-market-evidence",
                "valid_from": (NOW - timedelta(days=1)).isoformat(),
                "expires_at": (NOW + timedelta(days=30)).isoformat(),
                "distribution": {"low": 0.25, "base": 0.5, "high": 0.25},
            },
        )
        assert created.status_code == 200, created.text
        prior_id = created.json()["market_prior_id"]
        assert client.get(f"/api/v1/market-priors/{prior_id}").status_code == 200

        blocked = client.post(
            f"/api/v1/market-priors/{prior_id}/publish",
            headers=_headers("prior-publish-blocked"),
            json={},
        )
        assert blocked.status_code == 409

        reviewed = client.post(
            f"/api/v1/market-priors/{prior_id}/review",
            headers=_headers("prior-review"),
            json={},
        )
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["state"] == "REVIEWED"

        published = client.post(
            f"/api/v1/market-priors/{prior_id}/publish",
            headers=_headers("prior-publish"),
            json={},
        )
        assert published.status_code == 200, published.text
        assert published.json()["state"] == "PUBLISHED"
        assert (
            client.get(f"/api/v1/decision-units/{unit_id}/market-priors").json()["items"][0][
                "market_prior_id"
            ]
            == prior_id
        )


def test_unknown_entrant_and_subject_deduplication_exclude_named_competitors() -> None:
    unit_id = uuid4()
    with _client() as client:
        competitor = _create_competitor(client, key="unknown-named-competitor")
        canonical = competitor["canonical_subject_key"]

        missing_exclusion = client.post(
            f"/api/v1/decision-units/{unit_id}/unknown-entrant-profiles",
            headers=_headers("unknown-missing-exclusion"),
            json={
                "excluded_subject_keys": [],
                "count_distribution": {"0": 0.4, "1": 0.6},
                "evidence_refs": ["market-survey-2026"],
                "expires_at": (NOW + timedelta(days=30)).isoformat(),
            },
        )
        assert missing_exclusion.status_code == 422
        assert missing_exclusion.json()["code"] == "REQUEST_VALIDATION_FAILED"

        created = client.post(
            f"/api/v1/decision-units/{unit_id}/unknown-entrant-profiles",
            headers=_headers("unknown-create"),
            json={
                "excluded_subject_keys": [canonical],
                "count_distribution": {"0": 0.4, "1": 0.6},
                "evidence_refs": ["market-survey-2026"],
                "expires_at": (NOW + timedelta(days=30)).isoformat(),
            },
        )
        assert created.status_code == 200, created.text
        profile_id = created.json()["profile_id"]
        assert client.get(f"/api/v1/unknown-entrant-profiles/{profile_id}").status_code == 200
        assert (
            client.get(f"/api/v1/decision-units/{unit_id}/unknown-entrant-profiles").json()[
                "items"
            ][0]["profile_id"]
            == profile_id
        )

        published = client.post(
            f"/api/v1/unknown-entrant-profiles/{profile_id}/publish",
            headers=_headers("unknown-publish"),
            json={},
        )
        assert published.status_code == 200, published.text
        assert published.json()["state"] == "PUBLISHED"

        new_named = client.post(
            "/api/v1/competitors",
            headers=_headers("unknown-new-named-competitor"),
            json={
                "legal_name": "New Named Bidder Ltd",
                "canonical_subject_key": "new-named-bidder",
            },
        )
        assert new_named.status_code == 200, new_named.text
        assert (
            client.get(f"/api/v1/unknown-entrant-profiles/{profile_id}").json()["state"]
            == "QUARANTINED"
        )

        dedup = client.post(
            f"/api/v1/decision-units/{unit_id}/subject-deduplication-runs",
            headers=_headers("dedup-create"),
            json={"subject_keys": [" Example Bidder ", "examplebidder", "Other Bidder"]},
        )
        assert dedup.status_code == 200, dedup.text
        run = dedup.json()
        assert run["state"] == "SUCCEEDED"
        assert run["duplicate_groups"][canonical] == [
            " Example Bidder ",
            "examplebidder",
        ]
        assert canonical in run["named_subject_matches"]
        fetched = client.get(f"/api/v1/subject-deduplication-runs/{run['run_id']}")
        assert fetched.status_code == 200
        assert fetched.json() == run


def test_decision_unit_scope_and_strict_request_validation() -> None:
    allowed_unit = uuid4()
    denied_unit = uuid4()
    identity = _identity(
        all_decision_units=False,
        decision_unit_ids=frozenset({allowed_unit}),
    )
    app, authenticator, _ = _app(identity)
    with TestClient(app) as client:
        client.headers.update(AUTHORIZATION)
        denied = client.get(f"/api/v1/decision-units/{denied_unit}/market-priors")
        assert denied.status_code == 404
        assert denied.json()["code"] == "TENANT_SCOPE_VIOLATION"

        secret = client.post(
            "/api/v1/competitors",
            headers=_headers("secret-rejected"),
            json={
                "legal_name": "Unsafe Bidder",
                "canonical_subject_key": "unsafe-bidder",
                "api_key": "must-not-be-accepted",
            },
        )
        assert secret.status_code == 422

        competitor = _create_competitor(client, key="tenant-isolation")
        authenticator.identity = _identity(tenant_id=TENANT_B)
        hidden = client.get(f"/api/v1/competitors/{competitor['competitor_id']}")
        assert hidden.status_code == 404
        assert hidden.json()["code"] == "TENANT_SCOPE_VIOLATION"

        authenticator.identity = identity.model_copy(update={"roles": frozenset({Role.AUDITOR})})
        forbidden = client.post(
            "/api/v1/competitors",
            headers=_headers("permission-rejected"),
            json={
                "legal_name": "Forbidden Bidder",
                "canonical_subject_key": "forbidden-bidder",
            },
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["code"] == "PERMISSION_DENIED"
