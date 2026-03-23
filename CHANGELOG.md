# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed

- restructured project documentation so `README.md` stays public-facing while `docs\design.md` and `docs\implementation_plan.md` hold architecture and planning detail

### Planned

- Phase 2 search integration
- search result normalization
- initial service-layer wiring for retrieval

## [0.1.0] - Initial foundation

### Added

- project requirements document in `docs\requirements.md`
- system design document in `docs\design.md`
- FastAPI application scaffold under `src\agentic_browser\`
- environment-based settings and `.env.example`
- `GET /` and `GET /health` endpoints
- smoke tests for the current API surface
- `run.py`, `pyproject.toml`, `requirements.txt`, and `README.md`

### Repository

- initialized Git in the project directory
- created and pushed branch `phase1-foundation`
- opened pull request `#1` into `main`
- configured repo-local Git and credential settings for the personal GitHub account while leaving global Git settings unchanged
