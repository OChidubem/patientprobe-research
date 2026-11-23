# Research log / result record

## Current status

- Implemented: LiveKit synthetic patient infrastructure (research prototype), 12 scenario prompts, audio QA utilities, transcript processing, offline structured research evaluator, demo fixtures, and unit tests.
- Not demonstrated in this research edition: successful end-to-end research calls, verified agent failures, inter-rater reliability, real aggregate statistics, generalizable conclusions.

## Planned first real experiments

1. Document consent/authorization and the precise test system versions.
2. Run a smoke call using **only a privately configured, authorized test endpoint**, verifying two-sided audio and transcripts.
3. Label 3 clean and 3 correction trials before scaling up; check annotations against recordings.
4. Collect independent backend confirmation if testing booking/refill completion claims.
5. Run the evaluator on sanitized numeric annotations, record exclusions, and compare groups.

## Result table

No real trials have been added or analyzed. The example outputs are synthetic demonstrations and are **not research results**.

## Honest CV description (once repo is publicly sanitized)

*PatientProbe — Independent Research Software (in progress).* Developing a controlled evaluation framework for voice AI reliability under interruptions and ambiguous instructions; implemented reproducible, auditable scoring of annotated task outcomes and a structured plan for comparisons with clean-call baselines. Live-call research evaluation remains in progress.
