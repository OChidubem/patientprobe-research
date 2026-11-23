# Research protocol (prospective; not preregistered)

**Title:** PatientProbe: A reproducible evaluation framework for conversational AI reliability.

**Status:** Protocol and instrumentation implementation. This repository does **not** provide completed live-call results or evidence of research publication. The demo data are synthetic and must not be cited as experimental findings.

## Research questions

- **RQ1 — Instruction changes:** How often do conversational voice agents correctly retain a mid-dialogue correction, compared with equivalent clean requests?
- **RQ2 — Clarification:** When users give ambiguous requests, how often does an agent seek clarification instead of proceeding with an assumption?
- **RQ3 — Verifiable actions:** When an agent claims a task is complete, how often is the action verified by an independent backend audit or other authoritative state?
- **RQ4 — Interaction cost:** How do these conditions affect end-to-end task completion and observed response latency?

## Hypotheses (to test; no results claimed)

H1: Mid-dialogue correction scenarios will have lower task-completion rates than matched clean scenarios.

H2: Ambiguous requests will have more missed clarification opportunities than unambiguous requests.

H3: A transcript-only evaluation will be insufficient to establish false task-completion claims without independent system-state evidence.

## Conditions, experimental units, and baselines

- **Baseline:** an unperturbed, fully specified patient request using an authorized, documented test agent.
- **Interruption:** the same task goal but with a patient correction after the agent has started responding.
- **Ambiguity:** underspecified date, intent, or insurance-plan detail requiring clarification.
- **Noise (optional):** a documented controlled audio perturbation; use only if noise injection can be measured and is approved in the test setup.

The experimental unit is one completed, recorded call attempt; retain all attempts, including failures, in a private audit log. For a meaningful study, use matched scenarios across conditions, vary execution order, record model/provider versions, and conduct multiple repetitions. Planned minimum: at least five repetitions of each condition per scenario, **subject to authorized testing limits and costs**. The small initial study is descriptive, not a basis for broad generalization.

## Primary metrics and operational definitions

- **Task-completion rate:** proportion of trials with a verified completed user goal; label missing or unobservable outcomes `null` rather than failure.
- **Correction-retention rate:** proportion of trials with an explicit mid-call correction where the agent's final behavior reflects the corrected request.
- **Clarification rate:** proportion of trials requiring clarification where the agent asked the necessary question before acting.
- **False-confirmation rate:** proportion of calls with an agent confirmation *and* an independently verified failed action. Calls without state verification are excluded from this denominator; uncertainty is not evidence of false confirmation.
- **Response latency:** a manually or instrumentally observed delay in milliseconds with clearly specified start/end events. The current JSONL field is an annotation, not a proven audio-timestamp measure.

## Analysis strategy

Report each condition's numerator and denominator, percentage and a Wilson 95% interval (descriptive only), and median latency when observed. Summarize scenario-matched differences in task-completion rates between each changed condition and clean, where both exist. This comparison is descriptive and does not establish causality. Keep **synthetic fixtures out of real-study results**. Do not use a single aggregate score to hide per-scenario failures. Document exclusions and unsuccessful call attempts. Correlated repeats and model drift limit inferential claims.

## Annotation and quality control

Each trial must use the schema in `docs/DATA_DICTIONARY.md`. A human reviews the full two-sided audio and transcript. Backend outcomes require independent logged evidence; for real recordings, ideally have a second reviewer independently score at least a subset and reconcile disagreements. Keep logs with any decision to exclude a trial.

## Privacy and ethics

Use only an explicitly authorized test phone number and fictional patients. Never record or publish real patient data, private office information, or credentials. Obtain all recording permissions and follow applicable law. Publish only aggregated metrics and sanitized examples where authorized. All raw recordings and transcripts remain private.

## Limitations known before data collection

The optional live system requires a privately configured authorized test endpoint, explicit opt-in, and external API keys to place calls; none are included in the public repository. The offline research evaluator is functional; the live pipeline has not been independently validated as part of this research edition. The research protocol is a plan, not evidence that any hypotheses have been supported.
