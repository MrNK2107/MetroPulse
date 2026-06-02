# Changelog

All notable changes to MetroPulse are documented here. Format follows [Conventional Changelog](https://www.conventionalcommits.org/).

## [Unreleased]

### feat(api): add API versioning
- All REST routes now use `/api/v1` prefix (e.g. `/api/v1/health`, `/api/v1/regions`)
- Responses include `X-API-Version: 1` header via middleware
- Health route paths updated from `/api/health` to `/health` (relative to router prefix)

### feat(api): add request/response logging middleware
- Structured JSON logging for all non-health-check requests
- Logs include: `method`, `path`, `status`, `response_time_ms`
- Health endpoints (`/api/v1/health`, `/api/v1/health/data`) excluded from logging

### feat(api): add OpenAPI tags for better docs
- Tags: `Health`, `Regions`, `Simulation`, `Case Studies`, `Realtime`, `WebSocket`
- Each tag has a description visible in the `/docs` Swagger UI
- Route files updated to use the new tag names

### docs(architecture): improve ARCHITECTURE.md
- Added "Security Measures" section: rate limiting, WS limits, CORS policy, path traversal prevention, request logging
- Added "Testing Strategy" section: unit tests, integration tests, load tests, frontend tests, coverage targets
- Updated module map to reflect main.py middleware additions

### docs(readme): add API usage examples
- Added curl examples for all key REST endpoints
- Added WebSocket connection and message examples
- Added example JSON scenario input for simulation
