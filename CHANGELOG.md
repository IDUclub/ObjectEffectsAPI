## v0.4.4 (2026-10-20)

[fix/ICII-190-docker-log-rotation](https://github.com/IDUclub/ObjectEffectsAPI/pull/63) (#63)

- fix: cap container logs at 100 MB in docker compose
- fix: rotate the log file by size once a day and stop writing every record twice

## v0.4.3 (2026-10-02)

[refactor/uv](https://github.com/IDUclub/ObjectEffectsAPI/pull/62) (#62)

- refactor: manage dependencies with uv
- build: install the locked dependencies through the PyPI mirror

## v0.4.2 (2026-10-02)

[fix/version-status-token](https://github.com/IDUclub/ObjectEffectsAPI/pull/61) (#61)

- ci: set the passing version status with VERSION_STATUS_TOKEN so the merge starts the dev release

## v0.4.1 (2026-10-02)

[chore/versioning-policy](https://github.com/IDUclub/ObjectEffectsAPI/pull/60) (#60)

- ci: bump the version in the PR branch on auto-merge

