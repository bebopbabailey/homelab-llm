# Consistency Audit 2026-04

## Claims

| id | severity | surface | disposition | note |
| --- | --- | --- | --- | --- |
| DOC-2026-04-01 | high | Open Terminal live path | fix_now | Canonical live path is localhost direct backend; LiteLLM alias remains future work. |
| DOC-2026-04-02 | high | Gateway-only rule wording | fix_now | Clarified that direct backend URLs are operator-only or service-to-service paths, not client entrypoints. |
| DOC-2026-04-03 | high | OptiLLM proxy bind/auth drift | fix_now | Normalized docs to LAN bind `192.168.1.72:4020` and LiteLLM-first caller contract. |
| DOC-2026-04-04 | high | Inference retired lanes | fix_now | Removed `8100`/`8102` from active checks and rollback guidance. |
| DOC-2026-04-05 | high | Voice gateway bind ambiguity | fix_now | Normalized service spec to explicit Orin private LAN bind for production. |
| DOC-2026-04-06 | medium | Layer sandbox contradictions | fix_now | Clarified layer defaults vs service-local allowances. |
| DOC-2026-04-07 | medium | Broken internal markdown links | fix_now | Removed dead journal index links, corrected retired root-report reference, and added link audit tooling. |
