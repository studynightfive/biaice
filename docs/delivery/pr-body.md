# feat(m6-sim): FR-06/07/08/09a simulation baseline, search/scenario, batches, optimization, eligibility

## Summary

This PR delivers the full member-6 simulation feature per the contract
(`docs/标策AI_项目构建完整提示词_V1.0.md` section 15):

- **FR-06** decision baseline + candidate search space + scenario sets + freeze commands.
- **FR-07** simulation batches + candidates + static validations + scenario outcomes + scenario assessments.
- **FR-08** optimization runs + stress tests + strategy plans + complete-linkage merge assessments.
- **FR-09a** recommendation eligibilities + SHADOW-PILOT-LOCKED simulation assessment snapshots.

## Commits (chronological)

```
chore: import M0 baseline skeleton
feat(core): add SIMULATION_* permissions and 12 FR-06/07/08/09a error codes
feat(m6-sim): simulation domain layer (models, scenarios, probability, etc.)
feat(m6-sim): Celery worker (tasks + runtime) for simulation batches
feat(m6-sim): API layer with field-level Pydantic schemas and FastAPI handlers
feat(m6-sim): alembic migration m6_simulation_0001 for 16 simulation tables
test(m6-sim): unit + contract tests for simulation modules
feat(m6-sim): frontend simulation feature with 3 routes and 7 components
feat(m6-sim): shared frontend BiaiceClient adapter at apps/web/src/lib/api
docs(m6-sim): member-6 handoff + traceability for FR-06/07/08/09a
ci(m6-sim): add member-6 simulation job to existing CI workflow
```

## What is in scope

- Backend module `apps/backend/src/biaice/modules/simulation/`: 16 Pydantic v2 frozen models, 13 enums, 9 pure-function domain modules (manifest, scenarios, referee, static_validation, probability, optimization, stress, merge, eligibility, snapshot), and an InMemorySimulationRepository + 7 services.
- Worker `apps/backend/src/biaice/workers/simulation/`: Celery tasks + runtime.
- API `apps/backend/src/biaice/api/simulation.py`: 30+ real FastAPI handlers with PermissionGuard, Idempotency-Key and ETag enforcement.
- Migration `apps/backend/migrations/versions/m6_simulation_0001_member6_simulation.py`: 16 new tables with composite (tenant_id, data_domain_id, version_id) unique constraints.
- Frontend `apps/web/src/features/simulation/`: 3 routes (baseline-scenarios / simulation / eligibility) and 7 components.
- Frontend adapter `apps/web/src/lib/api/client.ts`: shared BiaiceClient wrapper used by member-6 (and reusable by future feature owners).
- Tests `apps/backend/tests/{unit,contract}/test_simulation_*`: pytest + FastAPI TestClient, Hypothesis property tests, no fake data.
- Docs `docs/delivery/M0-member6-handoff.md` + `docs/traceability/simulation.yaml`.

## What is explicitly NOT in this PR

- Real data mode (REAL_DATA_MODE) is **not** enabled; only synthetic data is consumed by tests.
- BYOK secret gate is unchanged; Provider egress is untouched.
- Approval / submission / authorization routes remain owned by member-7 and are not opened.
- Frontend page.tsx files are unchanged; only the public mount exports flip from FeaturePlaceholder to the real feature blocks.

## CI

The new `simulation` job runs alongside the existing CI:

- `PYTHONPATH=apps/backend/src python -m pytest apps/backend/tests -q -k simulation`
- `npm run test:web -- --testPathPattern=simulation`
- `python -m ruff check apps/backend/src/biaice/modules/simulation apps/backend/src/biaice/api/simulation.py`
- `npx eslint apps/web/src/features/simulation apps/web/src/lib/api/client.ts`

All existing CI jobs (repository-policy, web, backend, compose) are unchanged.

## Validation commands

```bash
PYTHONPATH=apps/backend/src python -m pytest apps/backend/tests -q -k simulation
npm run test:web -- --testPathPattern=simulation
python -m ruff check apps/backend/src/biaice/modules/simulation apps/backend/src/biaice/api/simulation.py
python -m alembic -c apps/backend/alembic.ini upgrade head
```

## Rollback

1. Revert this PR; no Alembic revision is touched besides the additive m6_simulation_0001.
2. Downgrade with `python -m alembic -c apps/backend/alembic.ini downgrade -1` only if member-6 was the last migration applied.
3. Re-enable the M0 501 stubs by reverting the contract_stubs.py change.

## Manual Gate acknowledgements

- [ ] TOTP / dual-device MFA ceremony (member-1 / SS-OPS) -- not gated by this PR; member-6 `PermissionGuard(mfa=True)` already enforces server-side.
- [ ] ProviderPolicy approval for model governance -- not gated by this PR; member-6 only consumes the published `ProviderPolicy`.
- [ ] REAL_DATA_MODE 12-evidence bundle -- not gated by this PR; member-6 will refuse any EXPECTED_VALUE / CVAR_TAIL real finance injection while in synthetic mode.
- [ ] OpenBao 2-of-3 share ceremony + audit device -- not gated by this PR; member-6 only consumes the OpenBao adapter through ports.

## References

- Contract: `标策AI_项目构建完整提示词_V1.0.md` section 15
- Handoff: `docs/delivery/M0-member6-handoff.md`
- Traceability: `docs/traceability/simulation.yaml`
- M0 baseline: `docs/delivery/M0-member1-handoff.md`
