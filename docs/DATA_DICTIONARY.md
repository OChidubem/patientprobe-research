# Research annotation schema

One JSON object per line in a JSONL file.

| Field | Type | Definition |
|---|---|---|
| `trial_id` | nonempty string | Unique call/attempt identifier |
| `scenario_id` | nonempty string | Scenario key; group matching scenarios under one key |
| `condition` | string | `clean`, `interruption`, `ambiguity`, or `noise` |
| `source` | string | `real` or `synthetic` (synthetic excluded by default) |
| `task_completed` | boolean/null | True only when outcome can be observed or verified |
| `correction_required` | boolean/null | Whether the patient gave a correction |
| `correction_honored` | boolean/null | Whether behavior matched correction; null unless required |
| `clarification_required` | boolean/null | Whether clarification was needed |
| `clarification_asked` | boolean/null | Whether agent sought clarification; null unless required |
| `confirmation_claimed` | boolean/null | Whether agent asserted task completed |
| `backend_action_verified` | boolean/null | Independent confirmation that action actually occurred; null if unavailable |
| `response_latency_ms` | nonnegative number/null | Measured response delay, with timing method documented |
| `reviewer` | nonempty string | Reviewer ID (fictional label in examples) |
| `evidence_ref` | nonempty string | Private local identifier; no patient information or direct public recording links |

**Semantics:** `false_confirmation_rate` only counts trials where `confirmation_claimed` is true and `backend_action_verified` is explicitly true/false. A missing backend verification is **unknown**, not a confirmed false claim. `correction_honored` and `clarification_asked` must be null when their respective `*_required` value is false or null. This prevents inflating denominators.

**Confidentiality:** Do not commit real transcripts, call audio, names, phone numbers, API responses containing private data, or raw audit logs. Use sanitized numeric annotations and private evidence references only. Use `data/examples/` for invented demonstrations, never observational evidence.
