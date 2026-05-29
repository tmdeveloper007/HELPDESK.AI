# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- AI-Generated Weekly Operations Digest Email with Admin Settings UI (#437)
- Cached SLA Breach Predictor & Interactive UI Estimate Badges (#434)
- Local backend setup and schema verification guide (#342, #351)

### Fixed
- Frontend: Map and persist image_url in ticket state generation
- Frontend: Blacklist invalid/expired API keys for failover optimization
- Frontend: Add 6s timeout to backend streaming fetch to prevent loading hang
- Frontend: Enforce client-side AI fallback on backend offline or 503 failures
- Resolve ticket store ID mismatch and improve ordering consistency (#352)
- Improve password error handling in admin signup (#400)
- Add auth to PATCH /tickets/{ticket_id} (#389)
- Invalidate server-side session on logout (#458)
- Add image size validation to prevent memory exhaustion DoS (#459)

### Changed
- WebSocket heartbeat from pong to ping (#381)
- Remove duplicate backend Dockerfile (#341)

### Security
- Add authentication to ticket update endpoint
- Implement server-side session invalidation on logout
- Add image size validation for DoS prevention

## [1.0.0] - 2025-02-19

### Added
- Initial release of HELPDESK.AI
- AI-powered ticket management system
- Multi-tenant support with company isolation
- Real-time notifications via WebSocket
- Admin dashboard with analytics
- Slack integration for ticket creation
- Email notifications for ticket updates
- Role-based access control (RBAC)
- Ticket categorization and prioritization
- Search and filtering capabilities
