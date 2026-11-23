# Research architecture

The project has two independent layers:

1. **Call collection (existing LiveKit prototype):** A synthetic caller uses an STT → text LLM → TTS pipeline. Outbound SIP is disabled by default and requires a locally configured approved destination and explicit opt-in; no destination is shipped with the public code. The system aims to retain raw transcripts, audio tracks, and call metadata in private local storage. Real calls require external services, credentials, and recording authorization. The included source code has offline unit tests but no verified end-to-end live-run results.
2. **Research annotation and evaluation (new):** Human reviewers produce structured JSONL annotations with grounded outcomes and optional independent backend verification. `patientprobe research` validates annotations and aggregates per-condition rates with explicit denominators. Synthetic fixtures are excluded unless `--include-synthetic` is provided. The evaluator makes no API calls.

```text
controlled scenarios -> authorized test calls -> private audio/transcripts
                                       -> evidence-backed annotations
                                              -> schema validation
                                              -> condition-specific metrics
                                              -> reproducible report
```

## Threats to validity

- Changes in model versions or agent policies can change outcomes between repetitions.
- Repeated calls to the same agent may be correlated and not independent.
- Recording/transcription quality may alter a human's interpretation; verify audio.
- Without system access, a statement such as “Your appointment is booked” cannot be determined to be true or false just from the transcript.
- The synthetic example data demonstrate software behavior only; never cite them as actual performance.

## Voice interface and evaluation components

This project retains the LiveKit Agents, Deepgram STT, OpenAI text LLM/TTS, SIP outbound, passive recorder, and scenario prompts. Those modules are a platform for planned experiments; the research contribution is the **experimental design and evidence-grounded evaluation**, not proof of new neural-network training or a peer-reviewed publication.
