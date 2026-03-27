# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Structured JSON logging with configurable log levels
- Request ID tracing middleware for distributed debugging
- Comprehensive `.dockerignore` to speed up Docker builds
- Makefile with common development commands (dev, test, lint, format, clean)
- Docker HEALTHCHECK for better container orchestration
- CHANGELOG.md for version tracking
- Environment-specific configuration support

### Changed
- **BREAKING**: Pinned all dependencies to specific versions for reproducible builds
- Replaced deprecated `@app.on_event()` with FastAPI lifespan context manager
- Enhanced logging in startup/shutdown lifecycle
- Improved middleware ordering (RequestID → ApiKey → CORS)

### Fixed
- N/A

### Security
- Added request ID tracking for security audit trails
- Improved error logging with structured format

## [1.0.0] - 2024-12-XX

### Added
- Initial release with voice-first ticketing platform
- 125+ MCP tools for AI voice agent integration
- FastAPI REST API with 18 router modules
- Stripe payment processing
- Email notifications via Resend
- SMS notifications via Twilio
- QR code ticket generation
- Apple Wallet pass generation
- PDF ticket downloads
- RAG knowledge base with semantic search
- Customer intelligence and churn prediction
- Marketing campaigns and auto-triggers
- Analytics and revenue forecasting
- Outbound webhooks with HMAC signing
- About page CMS
- Event photo gallery
- Multi-tier ticket pricing
- Promo codes and waitlist management
- Magic link authentication for admins
- 149 passing pytest tests
- Fly.io deployment configuration

### Documentation
- Comprehensive README with feature list
- API documentation via Swagger/OpenAPI
- Quick start guide
- Environment configuration examples

---

## Release Notes Format

Each release should follow this structure:

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security improvements
