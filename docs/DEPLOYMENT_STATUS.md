# Production deployment status

Verified 24 September 2026.

| Field | Value |
|---|---|
| Public production URL | https://phishing-classifier-beryl.vercel.app |
| Target / status | Production / READY; promoted successfully |
| Project | phishing-classifier |
| Deployment ID | dpl_FDYkApFVvgcWCvDfzLrjycfoH2Tw |
| Framework / runtime | Flask / Python 3.12 |
| Region | iad1 (Washington, D.C.) |
| Build command runtime | Vercel CLI 59.23.2; uv 0.10.11 |
| Local deployment CLI | Vercel CLI 59.16.0 |
| Build output generation | 6 seconds reported by the successful build |
| Dependency bundle before optimization | 231.18 MB reported by the builder |
| Git commit | Not available: downloaded working copy has no Git repository |
| Dashboard | https://vercel.com/ayushxdev1s-projects/phishing-classifier/FDYkApFVvgcWCvDfzLrjycfoH2Tw |

## Public verification

Unauthenticated requests to the public production URL returned the actual application, without redirecting to a Vercel login page:

- `/`: 200, HTML page.
- `/health`: 200, JSON health response.
- `/static/css/style.css`: 200, stylesheet; also checked against the local CSS bytes on the candidate deployment.
- `/sample`: 200, downloadable example CSV.
- `POST /predict`: 200, 837,054-byte CSV containing 11,055 predictions. Every class matched the original model fixture; `Cache-Control: no-store` was present.
- `POST /predict` without a file: 400, expected validation error.
- Browser inspection confirmed the styled public page, file picker, action button, sample link, and updated 4 MB / 30,000-row limits.

Machine-readable results: [production-verification.json](production-verification.json).

## Tests

- Python 3.11 training environment: 24 passed.
- Python 3.12 production environment: 22 passed, 2 training-only tests skipped.
- Portable export: 11,055 matching predictions plus 100 matching all-missing-feature rows.

## Post-deployment observability

- Queried this deployment's `error` and `fatal` runtime logs over the 30-minute window ending 2026-09-24 07:32:06 UTC. No matching log entries were found.
- Runtime logs are available through Vercel; no external log drain, error-tracking integration, or ongoing uptime monitor was configured by this task.
- This is a point-in-time verification, not a load test or availability guarantee.

Generated deployment/team URLs retain Vercel protection. Use the public URL above for end users, and `vercel curl` for protected candidate checks. Protection was not disabled.

The original candidate had a missing stylesheet caused by a broad ignore pattern. The final deployment listed above fixes that packaging issue and was verified after promotion. For future rollback, choose a fully verified deployment, not the initial candidate with the stylesheet defect.
