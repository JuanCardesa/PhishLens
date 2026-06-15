# Agent Instructions For PhishLens

PhishLens is a defensive cybersecurity project. Future AI agents and maintainers must follow these rules:

- Do not introduce offensive functionality, credential theft, attack automation, or abusive scraping.
- Do not capture passwords, typed emails, form values, full HTML, cookies, tokens, or private page content.
- Keep API keys and secrets out of the repository and out of the extension bundle.
- Follow Conventional Commits.
- Do not work directly on `main`.
- Keep extension, backend, ML, and documentation concerns separated.
- Add or update tests when changing backend services, scoring, schemas, or ML inference.
- Prefer privacy-preserving technical signals over raw content collection.
- Document important security, privacy, or architecture decisions in `docs/`.
- Keep Chrome permissions minimal and avoid remote code execution in the extension.
