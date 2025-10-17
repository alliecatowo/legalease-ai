# LegalEase Dashboard (Nuxt 4)

This package contains the authenticated dashboard used for case management, search, and transcript review. It is built with Nuxt 4, Nuxt UI, and VueUse.

## Running in Development

Infrastructure services (FastAPI, Postgres, Qdrant, MinIO, etc.) must already be running. The easiest approach is `make up-infra` from the repository root, or run the full stack with Docker and stop just the frontend container.

```bash
cd frontend
pnpm install
NUXT_PUBLIC_API_BASE=http://localhost:8000 pnpm dev
```

## Building for Production

```bash
pnpm build
pnpm preview
```

The Docker image defined in `docker/frontend/Dockerfile` is used by `docker-compose.yml` for the full stack.

## Notes

- `app/composables/useApi.ts` centralises REST calls; adjust base URLs or headers there.
- Shared caches live in `app/composables/useSharedData.ts` to avoid duplicate fetches between pages.
- Some UI surfaces (analytics, knowledge graph) currently contain placeholder data—backfill the backend endpoints before promoting them in documentation.
