# Free-tier deployment

Target: GitHub Pages frontend plus **Render Free** Python service. No paid service is selected by `render.yaml`.

The original in-process backend measured about 1.15 GB on Windows. Compact mode stores dictionary records in SQLite, maps quantized vectors/postings from disk, and isolates translation from embedding. The `runtime-1` asset release passed the original 512 MB test and was deployed on 18 October. The new speed update adds encoder reuse when memory permits and bounded caches; it requires a fresh container test. Docker is unavailable on this development computer, so local timings do not establish that the new runtime fits Render's limit.

## Deploying the speed update

No models, corpus or compact-export formats changed. Keep the current immutable `runtime-1` asset URL/checksum in Render; no asset rebuild is needed for this update.

1. In Render, set **Auto-Deploy → After CI Checks Pass**, or sync the updated Blueprint with `autoDeployTrigger: checksPass` before pushing the speed changes. This prevents deployment before the memory check completes.
2. Push the commits to `main`. **Project checks** builds the frontend, runs 28 backend tests and exercises repeated searches, distinct descriptions, Hindi translation/model switches and clues in a Docker container limited to **512 MB with no additional swap**. It reuses the checksum-pinned `runtime-1` archive and fails on OOM kills.
3. Let all checks pass before deploying the backend. If the memory check fails, inspect the logs and fix it; keep the Free plan. `SHABD_WARM_ENCODER=0` disables encoder retention as a fallback, while leaving caches and batched lookups available.
4. Run **Deploy frontend to GitHub Pages** to publish the one-time page-load health request. Frontend publication remains manual.
5. Verify new and repeated English/Hindi searches against the live site. Local timings are not production guarantees; the first request after inactivity can still wait for a free instance to start.

The original setup procedure below applies when creating a new service or changing resource assets.

## 1. Push and build verified resources

Push the committed code. In the repository's **Actions**, run **Build and verify free-tier runtime** on `main`. The first build downloads dictionaries/models and computes the index; allow up to 150 minutes. Standard public-repository GitHub-hosted runners are used.

The workflow builds the runtime Docker image and tests repeated English/Hindi requests with memory and swap both limited to 512 MB. It publishes a release only after success. If this job fails, inspect its container logs and fix the failure; do not select a paid Render plan as a workaround.

The release contains `runtime-assets.tar.gz` and `runtime-assets.tar.gz.sha256`. Copy the archive's HTTPS download link and the 64-character digest inside the checksum file. Use a specific release, not a mutable `latest` link.

## 2. Create the Render service

In your existing Render account, create a **Blueprint** from `Rohan-Ktksu/shabdanveshi`. Review `render.yaml`: service `shabdanveshi-api`, Docker runtime, plan **Free**, health path `/api/health`.

Set `ASSETS_URL` and `ASSETS_SHA256` from the successful release. The startup process verifies the archive checksum before extracting model/index files. It does not build the dictionary on the small runtime instance.

Confirm that `/api/health` returns HTTP 200 and `status: ready`. Run English and Hindi searches against the deployed `/api/predict` endpoint. Free services may sleep when idle; wake-up delay is expected. No persistent disk is required, but resources download again after a fresh instance starts.

## 3. Publish the frontend

In GitHub **Settings → Pages**, select **GitHub Actions** as the publishing source. In **Settings → Secrets and variables → Actions → Variables**, add `VITE_API_URL` with the Render service's HTTPS URL, without a trailing slash. This is public configuration, not a secret.

Run **Deploy frontend to GitHub Pages**. It checks API readiness before building the frontend. The intended address is `https://rohan-ktksu.github.io/shabdanveshi/`; it is not live merely because this file exists.

Finally check language selection, a real English search, a Hindi search with its interpreted text, source links, filters and narrow-screen layout. The backend CORS origin is already set to `https://rohan-ktksu.github.io`.

## Updating

Each meaningful stage remains a separate Git commit. Rebuild runtime assets when dictionary/model/retrieval-export settings change; update both Render asset settings to the new immutable release. Frontend publication is manual through its workflow. Keep credentials in service settings, never source files or chat.
