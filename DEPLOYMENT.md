# Free deployment: Vercel + GitHub Pages

The backend is being moved from Render Free to **Vercel Hobby**. The React website stays on GitHub Pages, keeping its existing address. The project remains at `D:\sem 5\ShabdAnveshi`.

Vercel Hobby Python functions have **2 GB RAM and 1 vCPU**, which gives the encoder room to remain loaded. Hobby is free for personal/non-commercial projects and has monthly usage limits; exceeding them can pause service. It is not unlimited hosting. See [Hobby limits](https://vercel.com/docs/plans/hobby) and [function resources](https://vercel.com/docs/functions/limitations).

## Backend project

1. Create/import `Rohan-Ktksu/shabdanveshi` into the personal **Hobby** workspace as `shabdanveshi-api`.
2. Keep the repository root as the project root and choose **FastAPI**. `pyproject.toml` resolves the app to `backend.main:app`; `.python-version` selects Python 3.12; the root requirements file includes only runtime dependencies.
3. Use Fluid Compute and set `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`. The public-beta Large Functions feature supports Python bundles up to 5 GB. This is needed to include the existing models/dictionary rather than downloading them on cold requests. New projects are enrolled by default; no Pro upgrade is selected. See [Large Functions](https://vercel.com/changelog/vercel-functions-can-now-be-up-to-5-gb-in-package-size-7yAwSyCig0IQDXUIDistvS/eadf06d6c3).
4. The configured build command, `python -m backend.vercel_build`, downloads the immutable `runtime-1` archive, verifies its SHA-256 and prepares the files for bundling. `vercel.json` includes the model, compact index and license directories. Assets are not published as static files.
5. Runtime settings in `vercel.json` select compact retrieval, one BLAS/OMP thread and the GitHub Pages CORS origin. They are public configuration, not credentials. Secrets and `.env` files are excluded from Git and CLI uploads.
6. The function region is Mumbai (`bom1`) and its request limit is 180 seconds. Free-plan memory remains managed by Vercel. Cold starts still exist; the new deployment does not promise instant first requests.

`backend/vercel_build.py` pins the archive URL and SHA-256. Update both only after a new verified resource release. Corpus/model settings did not change for this migration, so the existing resources can be reused.

## GitHub deployment

Connect the GitHub repository in the Vercel project so future pushes deploy the backend. If Vercel reports a missing GitHub Login Connection, connect GitHub under the Vercel account's authentication settings first. Grant access to this repository rather than unrelated repositories when the UI offers that choice.

The authenticated CLI can also publish the linked project with `vercel deploy --prod`. `.vercel/` metadata and local credentials are not committed.

**Project checks** runs the frontend build, 28 backend tests and a real API workload in a **2 GB container with no extra swap**. The runtime check also launches the original retrieval code at commit `d5ab2f5` on the same Linux runner and compares all 20 result lists. This avoids confusing CPU-dependent quantized inference differences with changes caused by caching or ranking optimizations.

## Switch the existing website

1. Verify the Vercel production API: health must report `ready`; new and repeated English/Hindi searches must return real suggestions; source links, clues and production CORS must work.
2. Set the GitHub Actions repository variable `VITE_API_URL` to that verified production API origin, without a trailing slash.
3. Run **Deploy frontend to GitHub Pages**. The workflow checks API readiness before publishing.
4. Verify the public website, including language settings, a real search and a repeat search. The page makes one health request when opened to start initialization while the user types.

Render auto-deploy is disabled in the dashboard and `render.yaml` during migration. The old Free service stays available temporarily as a fallback; the website should be switched only after Vercel has been tested. The legacy Render configuration does not select a paid plan.
