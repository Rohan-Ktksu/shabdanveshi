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

Update, 22 October 2026: the page-load health request compiles in the TypeScript/Vite GitHub Pages build. It runs once per mount, is aborted on unmount or after 90 seconds, and adds no visual changes. The backend now runs on Vercel Hobby. The repository variable `VITE_API_URL` is `https://shabdanveshi-api.vercel.app`; [Pages deployment 39799509663](https://github.com/Rohan-Ktksu/shabdanveshi/actions/runs/39799509663) succeeded. The published JavaScript bundle contains this new origin. The backend's full public API smoke test and its separate 2 GB CI check passed; see backend validation for diagnostic quality and timing limits.

Browser verification after deployment loaded the new `index-Vyb-YeLO.js` bundle and submitted `किताबों से प्रेम करने वाला व्यक्ति`. The page displayed `Interpreted as: A Lover of Books`, bibliophile first, its definition, WordNet source link and real similarity values. About retained the creator details, LinkedIn and repository links. The browser initially kept the prior HTML/bundle in cache; a fresh page URL loaded the new build. Existing visitors may need a hard refresh (Ctrl+Shift+R). A proof screenshot was saved locally at `.tools/live-search-vercel.png`.
