# ShabdAnveshi

Describe the thought. Discover the word.

A planned bilingual word finder for people who remember a meaning but cannot recall the word. This project extends Gorumutchu Rohan Sai's Natural Language Processing assignment on Similar Word Prediction.

## Current status

Design stage. The approved interface is **Quiet Conversation**, with a green palette, chat-based search, a first-visit language selector, language switching, settings and an About page. The preview uses illustrative results; the search engine and deployment are not implemented yet.

## Planned implementation

- React, TypeScript and Vite frontend.
- Python and FastAPI backend.
- English and Hindi descriptions and word suggestions, with separate interface and result-language preferences.
- Multilingual semantic retrieval with a TF-IDF baseline and optional clues.
- English WordNet and an appropriate licensed Hindi lexical resource. Corpus coverage and model choice require evaluation.
- GitHub Pages frontend and a separately hosted Python API, planned for Render.

Similarity scores will not be presented as probabilities. Ranking weights will be evaluated rather than assumed.

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
