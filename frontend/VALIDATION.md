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

Update, 18 October 2026: the API integration compiles, including the GitHub Pages base-path build. Live HTTP requests verify English/Hindi results, prefix filtering, source URLs and development CORS. The API now returns real dictionary results. Hindi search carries an experimental notice because its retrieval quality is uneven; see `../backend/VALIDATION.md`.

Browser inspection of the updated live results was blocked by the browser access policy. The visual checks above describe the earlier frontend stage, not the new live result rendering. Hosting and production CORS remain unverified.

The translation update adds the backend's interpreted query text to results and explains OPUS-MT in About. TypeScript and the production build pass; browser visual verification of these additions remains unavailable.
