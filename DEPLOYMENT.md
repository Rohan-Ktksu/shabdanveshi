# Free-tier deployment

Target: GitHub Pages frontend plus **Render Free** Python service. No paid service is selected by `render.yaml`.

The original in-process backend measured about 1.15 GB on Windows. The compact mode stores dictionary records in SQLite, maps quantized vectors/postings from disk, and runs translation and embedding in separate short-lived processes. This is slower but lowers resident memory. A local measurement is not proof that Render's limit is satisfied; the GitHub workflow must pass its hard 512 MB container test first. Docker is unavailable on this development computer, so that gate has not yet run.

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
