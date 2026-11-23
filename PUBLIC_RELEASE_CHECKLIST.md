# Public-release checklist

- [ ] Create a **new repository with a clean Git history**. Do not import or fork an previous project repository, whose commit history may still contain third-party names and a real telephone destination.
- [ ] Verify no credentials, real telephone endpoints, client names, private test instructions, or confidential terms appear anywhere in source, docs, or Git history.
- [ ] Confirm any inherited third-party materials and code may legally be reused and shared; if not, remove or rewrite them before publishing.
- [ ] Keep `.env`, private logs, recordings, and transcripts untracked; see `.gitignore`.
- [ ] Confirm `PATIENTPROBE_ENABLE_LIVE_CALLS=false` in `.env.example`; do not make paid or external calls during public testing.
- [ ] Run `python -m pytest -q` and the synthetic evaluator and review the output label.
- [ ] In academic CVs, describe this as **independent research software in progress** and never cite synthetic fixture numbers as real empirical findings.
- [ ] Verify all project claims are accurate and personally attributable before using them in graduate applications.
