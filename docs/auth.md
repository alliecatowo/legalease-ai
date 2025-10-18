# Authentication Stack

This repository now ships with a fully self-hosted Keycloak + Nuxt Auth Utils integration.

## Components

- **Keycloak**: runs inside Docker (see `docker-compose.yml`). It uses a dedicated Postgres schema and serves
  both the public (443) and admin APIs.
- **Nuxt Auth Utils**: manages sealed session cookies in the Nuxt frontend. OAuth flows are handled via
  custom BFF endpoints in `frontend/server/api/auth/*`.
- **FastAPI**: validates Keycloak access tokens, provisions local users, and enforces team level authorization.

## Environment Variables

The example file `docker/.env.auth.example` contains the required variables. Key entries:

| Variable | Description |
| --- | --- |
| `NUXT_SESSION_PASSWORD` | Secret used to seal Nuxt session cookies (≥32 chars). |
| `NUXT_PUBLIC_APP_URL` | Public URL for the dashboard (used for OAuth redirect URIs). |
| `KEYCLOAK_BACKEND_CLIENT_SECRET` | Service account secret used by the BFF to exchange authorization codes. |
| `NUXT_PUBLIC_KEYCLOAK_URL` / `REALM` / `CLIENT_ID` | Keycloak issuer details exposed to the browser. |

Copy the file to `docker/.env.auth` and adjust values before running `docker compose up`.

## Local Development

1. Install dependencies

   ```bash
   pnpm install --filter frontend
   pnpm install --filter backend
   pnpm install --filter landing # optional
   ```

2. Start the stack (Keycloak, proxy, backend services):

   ```bash
   docker compose up keycloak traefik postgres backend -d
   ```

3. Run the Nuxt dashboard:

   ```bash
   cd frontend
   pnpm dev
   ```

4. Visit `https://app.localhost/login` and authenticate with a Keycloak user that belongs to a `/teams/<slug>` group.

## Testing

Backend unit tests can be executed with:

```bash
cd backend
pytest
```

The suite currently includes coverage for the Keycloak team synchronizer (`tests/test_team_sync.py`).

For manual end-to-end validation:

1. Sign in via the dashboard login page.
2. Verify that the sidebar displays the correct team and that switching teams updates data.
3. Confirm API calls carry a `Bearer` token (inspect network panel). Unauthorized calls should trigger a redirect to `/login`.

## Refresh Tokens & Sessions

Access tokens and refresh tokens are stored inside the Nuxt session (the refresh token remains server-only via the `secure` session payload).
Tokens are refreshed whenever the user re-authenticates. For production, consider adding a silent refresh endpoint that exchanges
the refresh token before expiry.
