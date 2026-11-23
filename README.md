# PatientProbe

**A reproducible, evidence-oriented framework for studying conversational voice-agent reliability**

[Research protocol](docs/RESEARCH_PROTOCOL.md) · [Annotation schema](docs/DATA_DICTIONARY.md) · [Architecture](docs/ARCHITECTURE.md) · [Research status](docs/RESEARCH_NOTES.md)

> **Research status — November 2026:** Independent research software in progress. The pipeline, controlled scenario templates, research evaluation functions, and offline tests are implemented. No completed live-call study, empirical effect estimate, verified voice-agent failure, thesis, or peer-reviewed publication is claimed. The included example annotations are **synthetic fixtures**, not observations.

## Research motivation

Standard benchmarks often evaluate whether an AI system produces plausible responses, but not whether it preserves intent when requests change mid-conversation or whether claimed actions occurred. PatientProbe is designed to investigate the gap between *conversational fluency* and *verifiable task success*. It uses controlled patient-role scenarios in a test environment, not real patient interactions.

## Research questions

- **RQ1 — Corrections and distribution shift:** In matched task scenarios, does a mid-dialogue change of instructions affect task completion and correction retention?
- **RQ2 — Ambiguity:** Does an agent ask a necessary clarification question before acting on an underspecified request?
- **RQ3 — Evidence and execution:** Can an agent's claims about task completion be corroborated by system state rather than transcript appearance alone?
- **RQ4 — Interaction cost:** How do these conditions relate to response latency and unsuccessful call attempts?

**Hypotheses, baseline definitions, and planned analysis are documented in** [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md). Hypotheses are not findings.

## Research design

| Component | Implemented functionality | Evidence still required |
|---|---|---|
| Controlled scenarios | Synthetic caller prompts for scheduling, changes, ambiguity, interruption | Human-reviewed real test trials |
| Voice-test infrastructure | Python + LiveKit STT → text LLM → TTS components; local transcript/audio utilities | Authorized end-to-end provider and SIP validation |
| Evaluation | JSONL schema validation; condition-level task success, correction retention, clarification, backend-confirmation metrics | Outcome labels grounded in recordings and independent action logs |
| Reproducibility | Deterministic offline evaluator, unit tests, synthetic fixture, documented configuration | Repeated matched trials, stable target versions, uncertainty estimates |

The intended **unit of analysis is one attempted call**. Conditions should be paired by scenario and, where feasible, randomized in order. Human raters should annotate transcripts together with audio and authoritative task-state evidence. Unknown outcomes must remain unknown, rather than being scored automatically as failures. The current report generation uses descriptive rates and Wilson intervals; it does not establish causal effects by itself.

## Reproduce the offline evaluation

This does **not** access any phone network or require API credentials.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
patientprobe scenarios
patientprobe research --input data/examples/synthetic_trials.jsonl \
  --include-synthetic --output results/synthetic_demo.json
```

The example report is labeled **SYNTHETIC**. By default, the evaluator rejects synthetic trial records for real-study reports. See the [data dictionary](docs/DATA_DICTIONARY.md) for the evidence annotations required to use genuine observations.

## Optional live test infrastructure — disabled by default

The public repository contains **no target phone number, originating phone number, access token, or private evaluation-client identity**. Live SIP testing requires an independent test system under your control or explicit authorization, legally permitted recording, locally supplied credentials, and two separate opt-ins:

1. `PATIENTPROBE_APPROVED_DESTINATION` and `PATIENTPROBE_ENABLE_LIVE_CALLS=true` in a private `.env` file.
2. The `--confirm-live-calls` CLI argument or the explicit confirmation in `scripts/run.sh`.

Do not place calls to real patients, unapproved businesses, or unrelated third parties. Do not publish call audio, transcripts, secret credentials, identifiable information, or confidential organization details. **Use the offline evaluator for public demonstrations.**

## Repository layout

```text
src/patientprobe/   Voice-test components and evidence-grounded research evaluator
scripts/            Explicit opt-in runner (never run during offline tests)
data/examples/      Synthetic-only trial annotations
results/            Generated metrics (ignored by Git)
tests/              Automated offline validation
artifacts/          Locally stored, Git-ignored call artifacts
docs/               Protocol, architecture, schema, research notes
```

## Limitations and next steps

The present work implements instrumentation and a **prospective** study design, not completed empirical research. Planned next steps include independent voice-test validation; matched baseline versus interruption/ambiguity trials; transparent handling of missing ground truth; a second human rater for a subset; and a report of results with uncertainties and failure-case analysis. Until those experiments are performed, no robustness improvement or failure rate is claimed.

This project is not affiliated with or endorsed by any healthcare organization. All patient personas are fictional.
