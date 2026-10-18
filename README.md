# ShabdAnveshi

Describe the thought. Discover the word.

A bilingual word finder for people who remember a meaning but cannot recall the word. This project extends Gorumutchu Rohan Sai's Natural Language Processing assignment on Similar Word Prediction.

## Current status

The approved **Quiet Conversation** interface is implemented in React and TypeScript in `frontend/`, with a green palette, chat-based search, a first-visit language selector, language switching, settings and an expanded About page. A Python FastAPI service retrieves English and Hindi dictionary words using multilingual E5 embeddings and a small TF-IDF contribution. Sample conversations remain explicitly illustrative. Public deployment is not completed.

See [frontend setup and API contract](frontend/README.md) and [Python service setup](backend/README.md). Dictionary/model preparation runs once and resumes from checkpoints if interrupted. Generated assets and dependencies stay on the project's drive and are excluded from Git.

## Implementation

- React, TypeScript and Vite frontend.
- Python and FastAPI backend.
- English and Hindi descriptions and word suggestions, with separate interface and result-language preferences.
- Multilingual semantic retrieval with a TF-IDF baseline and optional clues.
- English WordNet 3.0 and Hindi Wiktionary entries extracted by Kaikki. Hindi words currently have English definitions, labeled in results. See [attribution and licenses](backend/ATTRIBUTION.md).
- GitHub Pages frontend and a separately hosted Python API, planned for Render.

Similarity scores are not probabilities. The current ranking is semantic cosine plus 0.05 times TF-IDF cosine, an uncalibrated starting point. `python -m backend.evaluate` runs a transparent 20-query smoke evaluation; it is not a representative accuracy benchmark.

The initial evaluation found an expected answer in the top five for 13 of 20 cases. Hindi retrieval is experimental and particularly weak on some negated descriptions. See [validation results](backend/VALIDATION.md) for examples and limitations; this prototype is not yet a reliable public release.

The updated compact pipeline reaches 16/20 top-five and 11/20 first-place matches on the same diagnostic set. It adds local Hindi query translation and an exact-gloss WordNet bridge. These are development-set results, not independent accuracy estimates; negation remains a limitation. [Free-tier deployment instructions](DEPLOYMENT.md) describe the GitHub Pages/Render setup and the mandatory 512 MB container check.

GitHub Actions checks the frontend build and Python contract/filter tests on pushes and pull requests. It does not download the full corpus or test model quality.

## Development stages

1. Record approved design and project requirements.
2. Build the responsive chat and About pages.
3. Add the Python API and lexical data preparation.
4. Implement and evaluate bilingual word retrieval.
5. Connect frontend and backend and test the complete workflow.
6. Configure deployment and publish verified URLs.

Each meaningful stage will be committed separately. The project is maintained at `D:\sem 5\ShabdAnveshi`.

## Design reference

`designs/concepts.html` contains the interactive design reference for the chat preview renderer. It relies on that renderer for carousel and icon support; it is not the deployable application.

## Author and academic details

- **Name:** Gorumutchu Rohan Sai
- **SRN:** R24EJ042
- **Class:** CSIT A, 5th Semester
- **Subject:** Natural Language Processing
- **Course code:** B25EJS503
- **Professor:** Arati C
- **Topic:** Similar Word Prediction

[LinkedIn](https://www.linkedin.com/in/rohansai0907) · [GitHub repository](https://github.com/Rohan-Ktksu/shabdanveshi)
