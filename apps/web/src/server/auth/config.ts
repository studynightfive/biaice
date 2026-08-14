type RequiredEnvironmentVariable =
  | "BIAICE_PUBLIC_ORIGIN"
  | "BIAICE_OIDC_ISSUER"
  | "BIAICE_OIDC_INTERNAL_ISSUER"
  | "BIAICE_OIDC_CLIENT_ID"
  | "API_INTERNAL_URL";

const EXPECTED_CLIENT_ID = "biaice-web";

export class BffConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BffConfigurationError";
  }
}

export type BffConfig = Readonly<{
  publicOrigin: string;
  publicIssuer: string;
  internalIssuer: string;
  clientId: string;
  apiInternalUrl: string;
  authorizationEndpoint: string;
  tokenEndpoint: string;
  logoutEndpoint: string;
  jwksEndpoint: string;
  callbackUrl: string;
  secureCookies: boolean;
}>;

function requiredValue(
  environment: NodeJS.ProcessEnv,
  name: RequiredEnvironmentVariable,
): string {
  const value = environment[name]?.trim();
  if (!value) {
    throw new BffConfigurationError(`Missing required BFF setting: ${name}`);
  }
  return value;
}

function parseHttpUrl(name: string, rawValue: string): URL {
  let url: URL;
  try {
    url = new URL(rawValue);
  } catch {
    throw new BffConfigurationError(`${name} must be an absolute HTTP(S) URL`);
  }
  if (!new Set(["http:", "https:"]).has(url.protocol)) {
    throw new BffConfigurationError(`${name} must use HTTP or HTTPS`);
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new BffConfigurationError(`${name} must not contain credentials, query, or fragment`);
  }
  return url;
}

function normalizeOrigin(name: string, rawValue: string): string {
  const url = parseHttpUrl(name, rawValue);
  if (url.pathname !== "/") {
    throw new BffConfigurationError(`${name} must be an origin without a path`);
  }
  return url.origin;
}

function normalizeEndpointBase(name: string, rawValue: string): string {
  const url = parseHttpUrl(name, rawValue);
  const pathname = url.pathname.replace(/\/+$/, "");
  return `${url.origin}${pathname}`;
}

export function readBffConfig(environment: NodeJS.ProcessEnv = process.env): BffConfig {
  const publicOrigin = normalizeOrigin(
    "BIAICE_PUBLIC_ORIGIN",
    requiredValue(environment, "BIAICE_PUBLIC_ORIGIN"),
  );
  const publicIssuer = normalizeEndpointBase(
    "BIAICE_OIDC_ISSUER",
    requiredValue(environment, "BIAICE_OIDC_ISSUER"),
  );
  const internalIssuer = normalizeEndpointBase(
    "BIAICE_OIDC_INTERNAL_ISSUER",
    requiredValue(environment, "BIAICE_OIDC_INTERNAL_ISSUER"),
  );
  const clientId = requiredValue(environment, "BIAICE_OIDC_CLIENT_ID");
  const apiInternalUrl = normalizeEndpointBase(
    "API_INTERNAL_URL",
    requiredValue(environment, "API_INTERNAL_URL"),
  );

  if (clientId !== EXPECTED_CLIENT_ID) {
    throw new BffConfigurationError(
      `BIAICE_OIDC_CLIENT_ID must be the registered public client ${EXPECTED_CLIENT_ID}`,
    );
  }

  const publicRealmPath = new URL(publicIssuer).pathname.replace(/\/+$/, "");
  const internalRealmPath = new URL(internalIssuer).pathname.replace(/\/+$/, "");
  if (!publicRealmPath || publicRealmPath !== internalRealmPath) {
    throw new BffConfigurationError(
      "BIAICE_OIDC_ISSUER and BIAICE_OIDC_INTERNAL_ISSUER must address the same realm path",
    );
  }

  return Object.freeze({
    publicOrigin,
    publicIssuer,
    internalIssuer,
    clientId,
    apiInternalUrl,
    authorizationEndpoint: `${publicIssuer}/protocol/openid-connect/auth`,
    tokenEndpoint: `${internalIssuer}/protocol/openid-connect/token`,
    logoutEndpoint: `${internalIssuer}/protocol/openid-connect/logout`,
    jwksEndpoint: `${internalIssuer}/protocol/openid-connect/certs`,
    callbackUrl: `${publicOrigin}/api/auth/callback`,
    secureCookies: new URL(publicOrigin).protocol === "https:",
  });
}
