"""M0 P0 operation catalog for real and deliberately CONTRACT_ONLY routers.

Paths and operationIds are frozen for parallel integration. An operation keeps
``STUB_FIELDS_PENDING_OWNER_FREEZE`` until its owner supplies strict field
schemas and a real handler; only those remaining entries receive 501 routes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True, slots=True)
class OperationSpec:
    method: str
    path: str
    operation_id: str
    fr: str
    owner: str
    permission: str
    summary: str
    idempotency_required: bool = False
    etag_required: bool = False
    schema_status: str = "STUB_FIELDS_PENDING_OWNER_FREEZE"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


_operations: list[OperationSpec] = []


def singularize(stem: str) -> str:
    """Return the catalog's canonical singular snake-case resource name."""

    if stem.endswith("ies"):
        return f"{stem[:-3]}y"
    return stem.removesuffix("s")


def add(
    method: str,
    path: str,
    operation_id: str,
    fr: str,
    owner: str,
    summary: str,
    *,
    permission: str | None = None,
    idempotency: bool | None = None,
    etag: bool = False,
    schema_status: str = "STUB_FIELDS_PENDING_OWNER_FREEZE",
) -> None:
    action = operation_id.split("_", 1)[0]
    write = method.upper() != "GET"
    _operations.append(
        OperationSpec(
            method=method.upper(),
            path=path,
            operation_id=operation_id,
            fr=fr,
            owner=owner,
            permission=permission or f"{fr.lower()}:{'read' if not write else action}",
            summary=summary,
            idempotency_required=(write and method.upper() != "PATCH")
            if idempotency is None
            else idempotency,
            etag_required=etag,
            schema_status=schema_status,
        )
    )


def collection(
    *,
    fr: str,
    owner: str,
    collection_path: str,
    item_path: str,
    stem: str,
    draft_update: bool = False,
    archive: bool = False,
) -> None:
    singular = singularize(stem)
    add(
        "GET",
        collection_path,
        f"list_{stem}",
        fr,
        owner,
        f"List {stem.replace('_', ' ')}",
    )
    add(
        "POST",
        collection_path,
        f"create_{singular}",
        fr,
        owner,
        f"Create {singular.replace('_', ' ')}",
    )
    add(
        "GET",
        item_path,
        f"get_{singular}",
        fr,
        owner,
        f"Get {singular.replace('_', ' ')}",
    )
    if draft_update:
        add(
            "PATCH",
            item_path,
            f"update_{singular}_draft",
            fr,
            owner,
            f"Update draft {singular.replace('_', ' ')}",
            etag=True,
        )
    if archive:
        add(
            "POST",
            f"{item_path}/archive",
            f"archive_{singular}",
            fr,
            owner,
            f"Archive {singular.replace('_', ' ')}",
        )


# FR-01 — member 2: projects, scope, regimes, rules and lifecycle.
collection(
    fr="FR-01",
    owner="member-2",
    collection_path="/api/v1/projects",
    item_path="/api/v1/projects/{project_id}",
    stem="projects",
    draft_update=True,
    archive=True,
)
collection(
    fr="FR-01",
    owner="member-2",
    collection_path="/api/v1/projects/{project_id}/decision-units",
    item_path="/api/v1/decision-units/{unit_id}",
    stem="decision_units",
    draft_update=True,
)
for resource, stem in [
    ("scope-assessments", "scope_assessments"),
    ("applicable-regimes", "applicable_regimes"),
    ("rule-sets", "rule_sets"),
    ("compliance-reviews", "compliance_reviews"),
    ("cross-lot-constraints", "cross_lot_constraints"),
]:
    singular = singularize(stem)
    collection(
        fr="FR-01",
        owner="member-2",
        collection_path=f"/api/v1/decision-units/{{unit_id}}/{resource}",
        item_path=f"/api/v1/{resource}/{{{singular}_id}}",
        stem=stem,
        draft_update=stem == "scope_assessments",
    )
for resource, stem in [
    ("scope-assessments", "scope_assessment"),
    ("applicable-regimes", "applicable_regime"),
    ("rule-sets", "rule_set"),
]:
    add(
        "POST",
        f"/api/v1/{resource}/{{{stem}_id}}/publish",
        f"publish_{stem}",
        "FR-01",
        "member-2",
        f"Publish {stem.replace('_', ' ')}",
    )
collection(
    fr="FR-01",
    owner="member-2",
    collection_path="/api/v1/rule-sets/{rule_set_id}/clauses",
    item_path="/api/v1/rule-clauses/{rule_clause_id}",
    stem="rule_clauses",
    draft_update=True,
)
add(
    "POST",
    "/api/v1/rule-clauses/{rule_clause_id}/supersede",
    "supersede_rule_clause",
    "FR-01",
    "member-2",
    "Supersede a published rule clause",
)
add(
    "POST",
    "/api/v1/compliance-reviews/{compliance_review_id}/transition",
    "transition_compliance_review",
    "FR-01",
    "member-2",
    "Transition compliance review",
)
add(
    "POST",
    "/api/v1/cross-lot-constraints/{cross_lot_constraint_id}/confirm",
    "confirm_cross_lot_constraint",
    "FR-01",
    "member-2",
    "Confirm cross-lot constraint",
)
add(
    "POST",
    "/api/v1/decision-units/{unit_id}/transition-commands",
    "submit_decision_unit_transition_command",
    "FR-01",
    "member-2",
    "Submit lifecycle transition command",
)
add(
    "GET",
    "/api/v1/decision-units/{unit_id}/lifecycle-events",
    "list_decision_unit_lifecycle_events",
    "FR-01",
    "member-2",
    "List append-only lifecycle events",
)

# FR-02 — member 3: secure upload, documents, parsing and replicas.
add(
    "POST",
    "/api/v1/projects/{project_id}/document-upload-sessions",
    "create_project_document_upload_session",
    "FR-02",
    "member-3",
    "Create project upload session",
)
add(
    "POST",
    "/api/v1/decision-units/{unit_id}/document-upload-sessions",
    "create_unit_document_upload_session",
    "FR-02",
    "member-3",
    "Create decision-unit upload session",
)
add(
    "GET",
    "/api/v1/document-upload-sessions/{session_id}",
    "get_document_upload_session",
    "FR-02",
    "member-3",
    "Get resumable upload status",
)
add(
    "PUT",
    "/api/v1/document-upload-sessions/{session_id}/chunks/{part_number}",
    "put_document_upload_chunk",
    "FR-02",
    "member-3",
    "Upload verified binary chunk",
)
add(
    "POST",
    "/api/v1/document-upload-sessions/{session_id}/complete",
    "complete_document_upload_session",
    "FR-02",
    "member-3",
    "Complete upload into quarantine",
)
add(
    "POST",
    "/api/v1/document-upload-sessions/{session_id}/cancel",
    "cancel_document_upload_session",
    "FR-02",
    "member-3",
    "Cancel upload and dispose temporary parts",
)
add(
    "GET",
    "/api/v1/projects/{project_id}/documents",
    "list_project_documents",
    "FR-02",
    "member-3",
    "List project documents",
)
add(
    "GET",
    "/api/v1/decision-units/{unit_id}/documents",
    "list_unit_documents",
    "FR-02",
    "member-3",
    "List decision-unit documents",
)
for action in ["inherit-to-unit", "override", "resolve-conflict", "detach"]:
    add(
        "POST",
        f"/api/v1/document-links/{action}",
        f"{action.replace('-', '_')}_document_link",
        "FR-02",
        "member-3",
        f"{action.replace('-', ' ').title()} document link",
    )
add(
    "GET",
    "/api/v1/documents/{document_id}",
    "get_document",
    "FR-02",
    "member-3",
    "Get document metadata",
)
for action in ["download", "review", "release-from-quarantine", "quarantine"]:
    add(
        "POST" if action != "download" else "GET",
        f"/api/v1/documents/{{document_id}}/{action}",
        f"{action.replace('-', '_')}_document",
        "FR-02",
        "member-3",
        f"{action.replace('-', ' ').title()} document",
    )
for scope_name, scope_path in [
    ("project", "projects/{project_id}"),
    ("unit", "decision-units/{unit_id}"),
]:
    add(
        "POST",
        f"/api/v1/{scope_path}/parse-jobs",
        f"create_{scope_name}_parse_job",
        "FR-02",
        "member-3",
        f"Create {scope_name} parse job",
    )
add(
    "GET",
    "/api/v1/parse-jobs/{parse_job_id}",
    "get_parse_job",
    "FR-02",
    "member-3",
    "Get parse job",
)
add(
    "POST",
    "/api/v1/parse-jobs/{parse_job_id}/retry",
    "retry_parse_job",
    "FR-02",
    "member-3",
    "Retry parse job",
)
add(
    "POST",
    "/api/v1/parse-jobs/{parse_job_id}/cancel",
    "cancel_parse_job",
    "FR-02",
    "member-3",
    "Cancel parse job",
)
add(
    "GET",
    "/api/v1/documents/{document_id}/derived-assets",
    "list_document_derived_assets",
    "FR-02",
    "member-3",
    "List document derived assets",
)
add(
    "GET",
    "/api/v1/derived-assets/{derived_asset_id}",
    "get_derived_asset",
    "FR-02",
    "member-3",
    "Get derived asset",
)
add(
    "GET",
    "/api/v1/replicas",
    "list_replicas",
    "FR-02",
    "member-3",
    "List registered replicas",
)

# FR-03/04 — member 4: evidence, precheck, conditions, cost and readiness.
for resource, stem, fr in [
    ("requirements", "requirements", "FR-03"),
    ("evidence", "evidence", "FR-03"),
    ("evidence-matches", "evidence_matches", "FR-03"),
    ("response-profiles", "response_profiles", "FR-03"),
    ("precheck-assessments", "precheck_assessments", "FR-03"),
    ("conditions", "conditions", "FR-03"),
    ("cost-baselines", "cost_baselines", "FR-04"),
    ("readiness-assessments", "readiness_assessments", "FR-04"),
]:
    singular = stem.removesuffix("s")
    collection(
        fr=fr,
        owner="member-4",
        collection_path=f"/api/v1/decision-units/{{unit_id}}/{resource}",
        item_path=f"/api/v1/{resource}/{{{singular}_id}}",
        stem=stem,
        draft_update=resource == "requirements",
    )
add(
    "GET",
    "/api/v1/decision-units/{unit_id}/commercial-policies",
    "list_commercial_policies",
    "FR-04",
    "member-4",
    "List commercial policies",
)
add(
    "POST",
    "/api/v1/decision-units/{unit_id}/commercial-policies",
    "create_commercial_policie",
    "FR-04",
    "member-4",
    "Create commercial policy",
)
add(
    "GET",
    "/api/v1/commercial-policies/{commercial_policie_id}",
    "get_commercial_policie",
    "FR-04",
    "member-4",
    "Get commercial policy",
)
for resource, stem, actions, fr in [
    ("requirements", "requirement", ["publish", "supersede"], "FR-03"),
    ("evidence", "evidence", ["review", "publish", "revoke"], "FR-03"),
    ("evidence-matches", "evidence_match", ["review"], "FR-03"),
    ("response-profiles", "response_profile", ["publish"], "FR-03"),
    ("conditions", "condition", ["satisfy", "waive", "fail", "expire"], "FR-03"),
    ("cost-baselines", "cost_baseline", ["approve", "publish"], "FR-04"),
    ("commercial-policies", "commercial_policy", ["publish"], "FR-04"),
]:
    for action in actions:
        add(
            "POST",
            f"/api/v1/{resource}/{{{stem}_id}}/{action}",
            f"{action}_{stem}",
            fr,
            "member-4",
            f"{action.title()} {stem.replace('_', ' ')}",
        )

# FR-05/12/13 — member 5: market, privacy and model/provider governance.
collection(
    fr="FR-05",
    owner="member-5",
    collection_path="/api/v1/competitors",
    item_path="/api/v1/competitors/{competitor_id}",
    stem="competitors",
    draft_update=True,
    archive=True,
)
collection(
    fr="FR-05",
    owner="member-5",
    collection_path="/api/v1/competitors/{competitor_id}/sources",
    item_path="/api/v1/competitor-sources/{competitor_source_id}",
    stem="competitor_sources",
)
for action in ["review", "quarantine"]:
    add(
        "POST",
        f"/api/v1/competitor-sources/{{competitor_source_id}}/{action}",
        f"{action}_competitor_source",
        "FR-05",
        "member-5",
        f"{action.title()} competitor source",
    )
add(
    "GET",
    "/api/v1/competitors/{competitor_id}/profiles",
    "list_competitor_profiles",
    "FR-05",
    "member-5",
    "List competitor profiles",
)
add(
    "POST",
    "/api/v1/competitors/{competitor_id}/profiles/build",
    "build_competitor_profile",
    "FR-05",
    "member-5",
    "Build governed competitor profile",
)
add(
    "GET",
    "/api/v1/competitor-profiles/{competitor_profile_id}",
    "get_competitor_profile",
    "FR-05",
    "member-5",
    "Get competitor profile",
)
add(
    "POST",
    "/api/v1/competitor-profiles/{competitor_profile_id}/publish",
    "publish_competitor_profile",
    "FR-05",
    "member-5",
    "Publish competitor profile",
)
for resource, stem in [
    ("market-priors", "market_priors"),
    ("unknown-entrant-profiles", "unknown_entrant_profiles"),
]:
    singular = singularize(stem)
    collection(
        fr="FR-05",
        owner="member-5",
        collection_path=f"/api/v1/decision-units/{{unit_id}}/{resource}",
        item_path=f"/api/v1/{resource}/{{{singular}_id}}",
        stem=stem,
    )
    if resource == "market-priors":
        add(
            "POST",
            "/api/v1/market-priors/{market_prior_id}/review",
            "review_market_prior",
            "FR-05",
            "member-5",
            "Review market prior",
        )
    add(
        "POST",
        f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}/publish",
        f"publish_{stem.removesuffix('s')}",
        "FR-05",
        "member-5",
        f"Publish {stem.removesuffix('s').replace('_', ' ')}",
    )
add(
    "POST",
    "/api/v1/decision-units/{unit_id}/subject-deduplication-runs",
    "create_subject_deduplication_run",
    "FR-05",
    "member-5",
    "Create subject deduplication run",
)
add(
    "GET",
    "/api/v1/subject-deduplication-runs/{run_id}",
    "get_subject_deduplication_run",
    "FR-05",
    "member-5",
    "Get subject deduplication run",
)

for resource, stem in [
    ("datasets", "datasets"),
    ("feature-schemas", "feature_schemas"),
    ("model-artifacts", "model_artifacts"),
    ("evaluation-protocols", "evaluation_protocols"),
    ("calibration-artifacts", "calibration_artifacts"),
    ("monitoring-snapshots", "monitoring_snapshots"),
    ("model-incidents", "model_incidents"),
    ("rollback-events", "rollback_events"),
]:
    collection(
        fr="FR-13",
        owner="member-5",
        collection_path=f"/api/v1/{resource}",
        item_path=f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}",
        stem=stem,
    )
    if resource in {
        "datasets",
        "feature-schemas",
        "model-artifacts",
        "evaluation-protocols",
    }:
        add(
            "POST",
            f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}/publish",
            f"publish_{stem.removesuffix('s')}",
            "FR-13",
            "member-5",
            f"Publish {stem.removesuffix('s').replace('_', ' ')}",
        )
add(
    "POST",
    "/api/v1/model-approvals",
    "create_model_approval",
    "FR-13",
    "member-5",
    "Create model approval",
    permission="fr-13:create+mfa",
)
add(
    "POST",
    "/api/v1/model-approvals/{model_approval_id}/decide",
    "decide_model_approval",
    "FR-13",
    "member-5",
    "Decide model approval",
    permission="fr-13:decide+mfa",
)
add(
    "POST",
    "/api/v1/model-deployments",
    "create_model_deployment",
    "FR-13",
    "member-5",
    "Create external model deployment binding",
    permission="fr-13:create+mfa",
)
for action in ["activate", "rollback"]:
    add(
        "POST",
        f"/api/v1/model-deployments/{{model_deployment_id}}/{action}",
        f"{action}_model_deployment",
        "FR-13",
        "member-5",
        f"{action.title()} model deployment",
        permission=f"fr-13:{action}+mfa",
    )

add(
    "GET",
    "/api/v1/ai-provider-catalog",
    "list_ai_provider_catalog",
    "FR-13",
    "member-5",
    "List published provider catalog",
    permission="fr-13:read",
    schema_status="FROZEN",
)
add(
    "POST",
    "/api/v1/platform/ai-provider-catalog-versions",
    "create_ai_provider_catalog_version",
    "FR-13",
    "member-5",
    "Create platform provider catalog version",
    permission="platform-provider-catalog:create+mfa",
    schema_status="FROZEN",
)
add(
    "GET",
    "/api/v1/platform/ai-provider-catalog-versions/{catalog_id}",
    "get_ai_provider_catalog_version",
    "FR-13",
    "member-5",
    "Get provider catalog version",
    permission="platform-provider-catalog:read",
    schema_status="FROZEN",
)
for action in ["publish", "revoke"]:
    add(
        "POST",
        f"/api/v1/platform/ai-provider-catalog-versions/{{catalog_id}}/{action}",
        f"{action}_ai_provider_catalog_version",
        "FR-13",
        "member-5",
        f"{action.title()} provider catalog version",
        permission=f"platform-provider-catalog:{action}+mfa",
        schema_status="FROZEN",
    )
add(
    "GET",
    "/api/v1/ai-provider-configurations",
    "list_ai_provider_configurations",
    "FR-13",
    "member-5",
    "List tenant provider configurations",
    permission="tenant-provider:read",
    schema_status="FROZEN",
)
add(
    "POST",
    "/api/v1/ai-provider-configurations",
    "create_ai_provider_configuration",
    "FR-13",
    "member-5",
    "Create draft provider configuration",
    permission="tenant-ai-admin:mfa",
    schema_status="FROZEN",
)
add(
    "GET",
    "/api/v1/ai-provider-configurations/{config_id}",
    "get_ai_provider_configuration",
    "FR-13",
    "member-5",
    "Get redacted provider configuration",
    permission="tenant-provider:read",
    schema_status="FROZEN",
)
add(
    "PATCH",
    "/api/v1/ai-provider-configurations/{config_id}",
    "update_ai_provider_configuration",
    "FR-13",
    "member-5",
    "Update draft provider configuration",
    permission="tenant-ai-admin:mfa",
    etag=True,
    schema_status="FROZEN",
)
for action, method, operation_id in [
    ("successors", "POST", "create_ai_provider_configuration_successor"),
    ("credential", "PUT", "set_ai_provider_credential"),
    ("credential", "DELETE", "revoke_ai_provider_credential"),
    ("test-connection", "POST", "test_ai_provider_connection"),
    ("activate", "POST", "activate_ai_provider_configuration"),
    ("suspend", "POST", "suspend_ai_provider_configuration"),
    ("revoke", "POST", "revoke_ai_provider_configuration"),
]:
    add(
        method,
        f"/api/v1/ai-provider-configurations/{{config_id}}/{action}",
        operation_id,
        "FR-13",
        "member-5",
        operation_id.replace("_", " ").title(),
        permission="tenant-ai-admin:mfa",
        schema_status="FROZEN",
    )
add(
    "GET",
    "/api/v1/provider-invocations",
    "list_provider_invocations",
    "FR-13",
    "member-5",
    "List redacted provider invocations",
    permission="tenant-provider:read",
    schema_status="FROZEN",
)
add(
    "GET",
    "/api/v1/provider-invocations/{invocation_id}",
    "get_provider_invocation",
    "FR-13",
    "member-5",
    "Get redacted provider invocation",
    permission="tenant-provider:read",
    schema_status="FROZEN",
)

for resource, stem in [
    ("processing-records", "processing_records"),
    ("legal-basis-evidence", "legal_basis_evidence"),
    ("notice-consent-records", "notice_consent_records"),
    ("pia-records", "pia_records"),
    ("cross-border-assessments", "cross_border_assessments"),
    ("load-profiles", "load_profiles"),
    ("data-subject-requests", "data_subject_requests"),
    ("incidents", "incidents"),
]:
    singular = singularize(stem)
    collection(
        fr="FR-12",
        owner="member-5",
        collection_path=f"/api/v1/{resource}",
        item_path=f"/api/v1/{resource}/{{{singular}_id}}",
        stem=stem,
    )
add(
    "GET",
    "/api/v1/provider-policies",
    "list_provider_policies",
    "FR-12",
    "member-5",
    "List provider policies",
    permission="fr-12:read",
)
add(
    "POST",
    "/api/v1/provider-policies",
    "create_provider_policie",
    "FR-12",
    "member-5",
    "Create provider policie",
    permission="fr-12:create",
)
add(
    "GET",
    "/api/v1/provider-policies/{provider_policie_id}",
    "get_provider_policie",
    "FR-12",
    "member-5",
    "Get provider policie",
    permission="fr-12:read",
)
add(
    "GET",
    "/api/v1/dsr-policies",
    "list_dsr_policies",
    "FR-12",
    "member-5",
    "List dsr policies",
    permission="fr-12:read",
)
add(
    "POST",
    "/api/v1/dsr-policies",
    "create_dsr_policie",
    "FR-12",
    "member-5",
    "Create dsr policie",
    permission="fr-12:create",
)
add(
    "GET",
    "/api/v1/dsr-policies/{dsr_policie_id}",
    "get_dsr_policie",
    "FR-12",
    "member-5",
    "Get dsr policie",
    permission="fr-12:read",
)
add(
    "GET",
    "/api/v1/incident-policies",
    "list_incident_policies",
    "FR-12",
    "member-5",
    "List incident policies",
    permission="fr-12:read",
)
add(
    "POST",
    "/api/v1/incident-policies",
    "create_incident_policie",
    "FR-12",
    "member-5",
    "Create incident policie",
    permission="fr-12:create",
)
add(
    "GET",
    "/api/v1/incident-policies/{incident_policie_id}",
    "get_incident_policie",
    "FR-12",
    "member-5",
    "Get incident policie",
    permission="fr-12:read",
)
for resource, stem, actions in [
    ("pia-records", "pia_record", ["approve", "revoke"]),
    (
        "cross-border-assessments",
        "cross_border_assessment",
        ["approve", "mark-not-required", "revoke", "expire"],
    ),
    (
        "provider-policies",
        "provider_policy",
        ["approve", "mark-not-required", "revoke", "expire"],
    ),
    ("dsr-policies", "dsr_policy", ["publish", "archive"]),
    ("load-profiles", "load_profile", ["freeze"]),
    (
        "data-subject-requests",
        "data_subject_request",
        ["verify-identity", "transition", "complete"],
    ),
    ("incident-policies", "incident_policy", ["approve"]),
    ("incidents", "incident", ["transition", "close"]),
]:
    for action in actions:
        add(
            "POST",
            f"/api/v1/{resource}/{{{stem}_id}}/{action}",
            f"{action.replace('-', '_')}_{stem}",
            "FR-12",
            "member-5",
            f"{action.replace('-', ' ').title()} {stem.replace('_', ' ')}",
        )
add(
    "POST",
    "/api/v1/consent-withdrawals",
    "append_consent_withdrawal",
    "FR-12",
    "member-5",
    "Append consent withdrawal event",
)

# FR-06/07/08/09a — member 6: baseline, simulation and recommendation eligibility.
for resource, stem, create_action in [
    ("decision-baselines", "decision_baselines", "freeze"),
    ("candidate-search-spaces", "candidate_search_spaces", "create"),
    ("scenario-sets", "scenario_sets", "create"),
]:
    add(
        "GET",
        f"/api/v1/decision-units/{{unit_id}}/{resource}",
        f"list_{stem}",
        "FR-06",
        "member-6",
        f"List {stem.replace('_', ' ')}",
    )
    add(
        "POST",
        f"/api/v1/decision-units/{{unit_id}}/{resource}/{create_action}"
        if create_action == "freeze"
        else f"/api/v1/decision-units/{{unit_id}}/{resource}",
        f"{create_action}_{stem.removesuffix('s')}",
        "FR-06",
        "member-6",
        f"{create_action.title()} {stem.removesuffix('s').replace('_', ' ')}",
    )
    add(
        "GET",
        f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}",
        f"get_{stem.removesuffix('s')}",
        "FR-06",
        "member-6",
        f"Get {stem.removesuffix('s').replace('_', ' ')}",
    )
    if resource == "scenario-sets":
        add(
            "POST",
            "/api/v1/scenario-sets/{scenario_set_id}/freeze",
            "freeze_scenario_set",
            "FR-06",
            "member-6",
            "Freeze scenario set",
        )
add(
    "POST",
    "/api/v1/decision-units/{unit_id}/simulation-batches",
    "create_simulation_batch",
    "FR-07",
    "member-6",
    "Create simulation batch",
)
add(
    "GET",
    "/api/v1/decision-units/{unit_id}/simulation-batches",
    "list_simulation_batches",
    "FR-07",
    "member-6",
    "List simulation batches",
)
add(
    "GET",
    "/api/v1/simulation-batches/{batch_id}",
    "get_simulation_batch",
    "FR-07",
    "member-6",
    "Get simulation batch",
)
for action in ["cancel", "retry"]:
    add(
        "POST",
        f"/api/v1/simulation-batches/{{batch_id}}/{action}",
        f"{action}_simulation_batch",
        "FR-07",
        "member-6",
        f"{action.title()} simulation batch",
    )
for child in [
    "candidates",
    "static-validations",
    "scenario-outcomes",
    "scenario-assessments",
]:
    add(
        "GET",
        f"/api/v1/simulation-batches/{{batch_id}}/{child}",
        f"list_simulation_batch_{child.replace('-', '_')}",
        "FR-07",
        "member-6",
        f"List batch {child.replace('-', ' ')}",
    )
add(
    "POST",
    "/api/v1/simulation-batches/{batch_id}/optimization-runs",
    "create_optimization_run",
    "FR-08",
    "member-6",
    "Create optimization run",
)
add(
    "GET",
    "/api/v1/simulation-batches/{batch_id}/optimization-runs",
    "list_optimization_runs",
    "FR-08",
    "member-6",
    "List optimization runs",
)
add(
    "GET",
    "/api/v1/optimization-runs/{run_id}",
    "get_optimization_run",
    "FR-08",
    "member-6",
    "Get optimization run",
)
for action in ["finalize", "invalidate"]:
    add(
        "POST",
        f"/api/v1/optimization-runs/{{run_id}}/{action}",
        f"{action}_optimization_run",
        "FR-08",
        "member-6",
        f"{action.title()} optimization run",
    )
for child in ["stress-test-assessments", "strategy-plans", "merge-assessments"]:
    add(
        "GET",
        f"/api/v1/optimization-runs/{{run_id}}/{child}",
        f"list_optimization_{child.replace('-', '_')}",
        "FR-08",
        "member-6",
        f"List optimization {child.replace('-', ' ')}",
    )
for action in ["publish", "invalidate"]:
    add(
        "POST",
        f"/api/v1/strategy-plans/{{strategy_plan_id}}/{action}",
        f"{action}_strategy_plan",
        "FR-08",
        "member-6",
        f"{action.title()} strategy plan",
    )
for resource, stem in [
    ("recommendation-eligibilities", "recommendation_eligibilities"),
    ("simulation-assessment-snapshots", "simulation_assessment_snapshots"),
]:
    add(
        "POST",
        f"/api/v1/decision-units/{{unit_id}}/{resource}",
        f"create_{stem.removesuffix('s')}",
        "FR-09a",
        "member-6",
        f"Create {stem.removesuffix('s').replace('_', ' ')}",
    )
    add(
        "GET",
        f"/api/v1/decision-units/{{unit_id}}/{resource}",
        f"list_{stem}",
        "FR-09a",
        "member-6",
        f"List {stem.replace('_', ' ')}",
    )
    add(
        "GET",
        f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}",
        f"get_{stem.removesuffix('s')}",
        "FR-09a",
        "member-6",
        f"Get {stem.removesuffix('s').replace('_', ' ')}",
    )
add(
    "GET",
    "/api/v1/simulation-assessment-snapshots/{simulation_assessment_snapshot_id}/download",
    "download_simulation_assessment_snapshot",
    "FR-09a",
    "member-6",
    "Download immutable simulation assessment snapshot",
)

# FR-09b/10 — member 7: approvals, reports, submission and outcomes.
collection(
    fr="FR-09b",
    owner="member-7",
    collection_path="/api/v1/approval-workflow-versions",
    item_path="/api/v1/approval-workflow-versions/{workflow_version_id}",
    stem="approval_workflow_versions",
    draft_update=True,
    archive=True,
)
add(
    "POST",
    "/api/v1/approval-workflow-versions/{workflow_version_id}/publish",
    "publish_approval_workflow_version",
    "FR-09b",
    "member-7",
    "Publish approval workflow version",
)
for resource, stem in [
    ("risk-acceptances", "risk_acceptances"),
    ("approval-packages", "approval_packages"),
    ("submission-authorizations", "submission_authorizations"),
]:
    action = "freeze" if resource == "approval-packages" else "create"
    path = f"/api/v1/decision-units/{{unit_id}}/{resource}"
    add(
        "POST",
        f"{path}/freeze" if action == "freeze" else path,
        f"{action}_{stem.removesuffix('s')}",
        "FR-09b",
        "member-7",
        f"{action.title()} {stem.removesuffix('s').replace('_', ' ')}",
    )
    add(
        "GET",
        path,
        f"list_{stem}",
        "FR-09b",
        "member-7",
        f"List {stem.replace('_', ' ')}",
    )
    add(
        "GET",
        f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}",
        f"get_{stem.removesuffix('s')}",
        "FR-09b",
        "member-7",
        f"Get {stem.removesuffix('s').replace('_', ' ')}",
    )
add(
    "POST",
    "/api/v1/risk-acceptances/{risk_acceptance_id}/revoke",
    "revoke_risk_acceptance",
    "FR-09b",
    "member-7",
    "Revoke risk acceptance",
)
add(
    "POST",
    "/api/v1/approval-packages/{approval_package_id}/approval-requests",
    "create_approval_request",
    "FR-09b",
    "member-7",
    "Create approval request",
)
add(
    "GET",
    "/api/v1/approval-requests/{approval_request_id}",
    "get_approval_request",
    "FR-09b",
    "member-7",
    "Get approval request",
)
add(
    "POST",
    "/api/v1/approval-requests/{approval_request_id}/cancel",
    "cancel_approval_request",
    "FR-09b",
    "member-7",
    "Cancel approval request",
)
add(
    "GET",
    "/api/v1/workflow-instances/{workflow_instance_id}",
    "get_workflow_instance",
    "FR-09b",
    "member-7",
    "Get workflow instance",
)
add(
    "GET",
    "/api/v1/workflow-instances/{workflow_instance_id}/steps",
    "list_approval_steps",
    "FR-09b",
    "member-7",
    "List approval steps",
)
add(
    "POST",
    "/api/v1/approval-steps/{approval_step_id}/decisions",
    "append_approval_decision",
    "FR-09b",
    "member-7",
    "Append immutable approval decision",
)
add(
    "GET",
    "/api/v1/approval-packages/{approval_package_id}/applicability-events",
    "list_approval_applicability_events",
    "FR-09b",
    "member-7",
    "List approval applicability events",
)
for action in ["block", "expire"]:
    add(
        "POST",
        f"/api/v1/submission-authorizations/{{submission_authorization_id}}/{action}",
        f"{action}_submission_authorization",
        "FR-09b",
        "member-7",
        f"{action.title()} submission authorization",
    )

for report in ["precheck-reports", "decision-reports"]:
    stem = report.replace("-", "_")
    add(
        "POST",
        f"/api/v1/decision-units/{{unit_id}}/{report}",
        f"create_{stem.removesuffix('s')}",
        "FR-10",
        "member-7",
        f"Create {stem.removesuffix('s').replace('_', ' ')}",
    )
    add(
        "GET",
        f"/api/v1/decision-units/{{unit_id}}/{report}",
        f"list_{stem}",
        "FR-10",
        "member-7",
        f"List {stem.replace('_', ' ')}",
    )
    add(
        "GET",
        f"/api/v1/{report}/{{report_id}}",
        f"get_{stem.removesuffix('s')}",
        "FR-10",
        "member-7",
        f"Get {stem.removesuffix('s').replace('_', ' ')}",
    )
    add(
        "GET",
        f"/api/v1/{report}/{{report_id}}/download",
        f"download_{stem.removesuffix('s')}",
        "FR-10",
        "member-7",
        f"Download {stem.removesuffix('s').replace('_', ' ')}",
    )
add(
    "POST",
    "/api/v1/decision-units/{unit_id}/submission-records",
    "create_submission_record_draft",
    "FR-10",
    "member-7",
    "Create submission record draft",
)
add(
    "GET",
    "/api/v1/decision-units/{unit_id}/submission-records",
    "list_submission_records",
    "FR-10",
    "member-7",
    "List submission records",
)
add(
    "GET",
    "/api/v1/submission-records/{submission_record_id}",
    "get_submission_record",
    "FR-10",
    "member-7",
    "Get submission record",
)
add(
    "PATCH",
    "/api/v1/submission-records/{submission_record_id}",
    "update_submission_record_draft",
    "FR-10",
    "member-7",
    "Update submission draft",
    etag=True,
)
for action in ["declare", "verify", "mark-mismatch", "mark-failed", "withdraw"]:
    add(
        "POST",
        f"/api/v1/submission-records/{{submission_record_id}}/{action}",
        f"{action.replace('-', '_')}_submission_record",
        "FR-10",
        "member-7",
        f"{action.replace('-', ' ').title()} submission record",
    )
for child in ["artifacts", "attempts"]:
    add(
        "POST",
        f"/api/v1/submission-records/{{submission_record_id}}/{child}",
        f"append_submission_{child.removesuffix('s')}",
        "FR-10",
        "member-7",
        f"Append submission {child.removesuffix('s')}",
    )
    add(
        "GET",
        f"/api/v1/submission-records/{{submission_record_id}}/{child}",
        f"list_submission_{child}",
        "FR-10",
        "member-7",
        f"List submission {child}",
    )
for action in ["freeze", "compare-to-approval-package"]:
    add(
        "POST",
        f"/api/v1/submission-artifacts/{{submission_artifact_id}}/{action}",
        f"{action.replace('-', '_')}_submission_artifact",
        "FR-10",
        "member-7",
        f"{action.replace('-', ' ').title()} submission artifact",
    )
add(
    "POST",
    "/api/v1/decision-units/{unit_id}/procurement-outcomes",
    "create_procurement_outcome",
    "FR-10",
    "member-7",
    "Create procurement outcome",
)
add(
    "GET",
    "/api/v1/decision-units/{unit_id}/procurement-outcomes",
    "list_procurement_outcomes",
    "FR-10",
    "member-7",
    "List procurement outcomes",
)
add(
    "GET",
    "/api/v1/outcomes/{outcome_id}",
    "get_procurement_outcome",
    "FR-10",
    "member-7",
    "Get procurement outcome",
)
for action in ["verify", "mark-conflicting"]:
    add(
        "POST",
        f"/api/v1/outcomes/{{outcome_id}}/{action}",
        f"{action.replace('-', '_')}_procurement_outcome",
        "FR-10",
        "member-7",
        f"{action.replace('-', ' ').title()} procurement outcome",
    )
add(
    "POST",
    "/api/v1/outcomes/{outcome_id}/conflict-resolution-events",
    "append_outcome_conflict_resolution_event",
    "FR-10",
    "member-7",
    "Append outcome conflict resolution",
)
add(
    "GET",
    "/api/v1/outcomes/{outcome_id}/conflict-resolution-events",
    "list_outcome_conflict_resolution_events",
    "FR-10",
    "member-7",
    "List outcome conflict resolution events",
)
for event in ["lifecycle-events", "revocation-events"]:
    add(
        "POST",
        f"/api/v1/reports/{{report_id}}/{event}",
        f"append_report_{event.replace('-', '_').removesuffix('s')}",
        "FR-10",
        "member-7",
        f"Append report {event.replace('-', ' ').removesuffix('s')}",
    )
    add(
        "GET",
        f"/api/v1/reports/{{report_id}}/{event}",
        f"list_report_{event.replace('-', '_')}",
        "FR-10",
        "member-7",
        f"List report {event.replace('-', ' ')}",
    )

# FR-11 — member 1 APIs are contract-only until the PostgreSQL adapter lands.
add(
    "GET",
    "/api/v1/objects/{object_type}/{object_id}/lineage",
    "get_object_lineage",
    "FR-11",
    "member-1",
    "Get actual dependency lineage",
    permission="governance:read",
)
add(
    "GET",
    "/api/v1/objects/{object_type}/{object_id}/input-manifest",
    "get_object_input_manifest",
    "FR-11",
    "member-1",
    "Get typed input manifest",
    permission="governance:read",
)
add(
    "POST",
    "/api/v1/supersession-events",
    "append_supersession_event",
    "FR-11",
    "member-1",
    "Append supersession event",
    permission="governance:write",
)
add(
    "GET",
    "/api/v1/supersession-events",
    "list_supersession_events",
    "FR-11",
    "member-1",
    "List supersession events",
    permission="governance:read",
)
add(
    "GET",
    "/api/v1/invalidation-events",
    "list_invalidation_events",
    "FR-11",
    "member-1",
    "List invalidation events",
    permission="governance:read",
)
add(
    "GET",
    "/api/v1/invalidation-events/{invalidation_id}",
    "get_invalidation_event",
    "FR-11",
    "member-1",
    "Get invalidation event",
    permission="governance:read",
)
for resource, stem in [
    ("retention-jobs", "retention_jobs"),
    ("deletion-jobs", "deletion_jobs"),
]:
    add(
        "GET",
        f"/api/v1/{resource}",
        f"list_{stem}",
        "FR-11",
        "member-1",
        f"List {stem.replace('_', ' ')}",
        permission="governance:read",
    )
    add(
        "POST",
        f"/api/v1/{resource}",
        f"create_{stem.removesuffix('s')}",
        "FR-11",
        "member-1",
        f"Create {stem.removesuffix('s').replace('_', ' ')}",
        permission="governance:write",
    )
    add(
        "GET",
        f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}",
        f"get_{stem.removesuffix('s')}",
        "FR-11",
        "member-1",
        f"Get {stem.removesuffix('s').replace('_', ' ')}",
        permission="governance:read",
    )
    add(
        "POST",
        f"/api/v1/{resource}/{{{stem.removesuffix('s')}_id}}/retry",
        f"retry_{stem.removesuffix('s')}",
        "FR-11",
        "member-1",
        f"Retry {stem.removesuffix('s').replace('_', ' ')}",
        permission="governance:write",
    )
add(
    "GET",
    "/api/v1/legal-holds",
    "list_legal_holds",
    "FR-11",
    "member-1",
    "List legal holds",
    permission="governance:read",
)
add(
    "POST",
    "/api/v1/legal-holds",
    "create_legal_hold",
    "FR-11",
    "member-1",
    "Create legal hold",
    permission="legal-hold:manage",
)
add(
    "POST",
    "/api/v1/legal-holds/{legal_hold_id}/release",
    "release_legal_hold",
    "FR-11",
    "member-1",
    "Release legal hold with dual control",
    permission="legal-hold:release",
)
add(
    "POST",
    "/api/v1/legal-hold-overrides",
    "create_legal_hold_override",
    "FR-11",
    "member-1",
    "Create legal hold override",
    permission="legal-hold:release",
)
add(
    "GET",
    "/api/v1/deletion-jobs/{deletion_job_id}/replica-commands",
    "list_deletion_replica_commands",
    "FR-11",
    "member-1",
    "List deletion replica commands",
    permission="governance:read",
)
add(
    "GET",
    "/api/v1/deletion-jobs/{deletion_job_id}/receipts",
    "list_deletion_receipts",
    "FR-11",
    "member-1",
    "List deletion receipts",
    permission="governance:read",
)
add(
    "GET",
    "/api/v1/tombstones",
    "list_tombstones",
    "FR-11",
    "member-1",
    "List minimal tombstones",
    permission="governance:read",
)
add(
    "GET",
    "/api/v1/tombstones/{tombstone_id}",
    "get_tombstone",
    "FR-11",
    "member-1",
    "Get minimal tombstone",
    permission="governance:read",
)
add(
    "GET",
    "/api/v1/audit-events",
    "list_audit_events",
    "FR-11",
    "member-1",
    "List authorized audit metadata",
    permission="audit:read",
)
add(
    "POST",
    "/api/v1/audit-integrity-checks",
    "create_audit_integrity_check",
    "FR-11",
    "member-1",
    "Run audit integrity check",
    permission="audit:integrity:run",
)
add(
    "GET",
    "/api/v1/audit-integrity-checks/{integrity_check_id}",
    "get_audit_integrity_check",
    "FR-11",
    "member-1",
    "Get audit integrity result",
    permission="audit:read",
)


# Member 5 has replaced every FR-05/FR-12/FR-13 contract stub with a strict,
# tested handler. Keep the source catalog aligned with that implemented state;
# the explicit Provider entries above remain useful documentation at the call site.
OPERATION_CATALOG: tuple[OperationSpec, ...] = tuple(
    replace(operation, schema_status="FROZEN")
    if operation.owner == "member-5"
    else operation
    for operation in _operations
)


def validate_operation_catalog() -> None:
    operation_ids = [item.operation_id for item in OPERATION_CATALOG]
    if len(operation_ids) != len(set(operation_ids)):
        duplicates = sorted(
            {item for item in operation_ids if operation_ids.count(item) > 1}
        )
        raise RuntimeError(f"duplicate operationIds: {duplicates}")
    route_keys = [(item.method, item.path) for item in OPERATION_CATALOG]
    if len(route_keys) != len(set(route_keys)):
        duplicates = sorted({item for item in route_keys if route_keys.count(item) > 1})
        raise RuntimeError(f"duplicate method/path pairs: {duplicates}")
    required_frs = {f"FR-{number:02d}" for number in range(1, 9)} | {
        "FR-09a",
        "FR-09b",
        "FR-10",
        "FR-11",
        "FR-12",
        "FR-13",
    }
    covered_frs = {item.fr for item in OPERATION_CATALOG}
    missing = required_frs - covered_frs
    if missing:
        raise RuntimeError(
            f"P0 operation groups missing from catalog: {sorted(missing)}"
        )


validate_operation_catalog()
