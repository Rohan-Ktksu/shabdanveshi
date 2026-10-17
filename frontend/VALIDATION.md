# Frontend validation

Checked on 17 October 2026.

- TypeScript strict compilation and Vite production build pass.
- First-visit language dialog opens and can select English.
- Language changes to Hindi; Hindi preference survives a reload without reopening onboarding.
- Changing interface language does not overwrite the separately selected result language.
- Sample conversation displays two English or two Hindi words and is explicitly labelled illustrative.
- Disabling definitions in settings hides result definitions.
- Submitting a description without API configuration gives a clear disconnected-service message and preserves the query.
- About page contains the project journey, planned search logic, technology status and student details.
- LinkedIn and repository anchors point to the user-provided URLs.
- At the narrow viewport checked (390 pixels requested, 375-pixel document content area), About and chat document widths equal the viewport width; no horizontal overflow.

Not yet verified: live Python API responses, semantic retrieval quality, corpus coverage, hosting or production CORS. These belong to later implementation stages.
