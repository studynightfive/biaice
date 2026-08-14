"""Regression checks for the fail-closed Keycloak realm and synthetic bootstrap."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REALM = json.loads((ROOT / "infra/keycloak/biaice-realm.json").read_text(encoding="utf-8"))
USER_PROFILE = json.loads(
    (ROOT / "infra/keycloak/user-profile.json").read_text(encoding="utf-8")
)
INIT_SCRIPT = (ROOT / "infra/keycloak/init.sh").read_text(encoding="utf-8")


class KeycloakContractTests(unittest.TestCase):
    def test_web_client_emits_api_identity_contract(self) -> None:
        web = next(client for client in REALM["clients"] if client["clientId"] == "biaice-web")
        self.assertTrue(web["publicClient"])
        self.assertTrue(web["standardFlowEnabled"])
        self.assertFalse(web["directAccessGrantsEnabled"])
        self.assertEqual(web["attributes"]["pkce.code.challenge.method"], "S256")
        self.assertIn("basic", web["defaultClientScopes"])

        mappers = {mapper["name"]: mapper for mapper in web["protocolMappers"]}
        expected_attributes = {
            "biaice-tenant-id": ("tenant_id", "tenant_id", "false"),
            "biaice-data-domain-id": ("data_domain_id", "data_domain_id", "false"),
            "biaice-project-ids": ("project_ids", "project_ids", "true"),
            "biaice-decision-unit-ids": (
                "decision_unit_ids",
                "decision_unit_ids",
                "true",
            ),
        }
        for name, (attribute, claim, multivalued) in expected_attributes.items():
            config = mappers[name]["config"]
            self.assertEqual(config["user.attribute"], attribute)
            self.assertEqual(config["claim.name"], claim)
            self.assertEqual(config["multivalued"], multivalued)
            self.assertEqual(config["access.token.claim"], "true")
        self.assertEqual(
            mappers["biaice-authentication-method-reference"]["protocolMapper"],
            "oidc-amr-mapper",
        )

    def test_scope_attributes_are_admin_only_unmanaged_metadata(self) -> None:
        self.assertEqual(USER_PROFILE["unmanagedAttributePolicy"], "ADMIN_EDIT")
        self.assertEqual(
            {attribute["name"] for attribute in USER_PROFILE["attributes"]},
            {"username", "email", "firstName", "lastName"},
        )

    def test_synthetic_bootstrap_covers_all_roles_and_scope_fields(self) -> None:
        realm_roles = {role["name"] for role in REALM["roles"]["realm"]}
        assigned_roles: set[str] = set()
        for roles_csv in re.findall(r'ensure_user\s+\S+\s+\S+\s+"\$\S+"\s+"([A-Z_,]+)"', INIT_SCRIPT):
            assigned_roles.update(roles_csv.split(","))
        self.assertTrue(assigned_roles)
        self.assertLessEqual(assigned_roles, realm_roles)
        for claim in ("tenant_id", "data_domain_id", "project_ids", "decision_unit_ids"):
            self.assertIn(f'"{claim}"', INIT_SCRIPT)
        self.assertIn("sed 's/\\r$//'", INIT_SCRIPT)
        self.assertIn("invalidPasswordHistoryMessage", INIT_SCRIPT)


if __name__ == "__main__":
    unittest.main()
