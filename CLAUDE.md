# Claude Code Instructions

## Build System

- Always use `mise` to run scripts. Treat mise like make.
- `mise run dev:local` - Full local development with Firebase emulators
- `mise run build:functions` - Build Firebase Functions
- `mise run deploy` - Deploy to production

## Project Structure

```
legalease-ai/
├── frontend/          # Nuxt 4 dashboard (pnpm)
├── functions/         # Firebase Functions + Genkit (npm)
├── landing/           # Marketing site (pnpm)
└── docker-compose.yml # Qdrant, Docling services
```

## Key Patterns

### Frontend (Nuxt 4)
- Composables in `frontend/app/composables/` for Firebase integration
- All composables have SSR guards (`import.meta.server` checks)
- Firebase initialized in `app/plugins/firebase.client.ts`
- Provider-aware emulator routing for Storage

### Functions (Firebase + Genkit)
- Flows in `functions/src/flows/` (transcription, summarization, search)
- Transcription providers in `functions/src/transcription/providers/`
- Config centralized in `functions/src/config.ts`
- Triggers in `functions/src/index.ts`

### Transcription Providers
- `gemini` (default): Works with Storage emulator, uses `@google/genai`
- `chirp`: Requires production GCS, uses Speech-to-Text V2 API
- Provider pattern: each declares `requiresProduction.storage`

## Environment Variables

For local development with emulators, only need:
- `GOOGLE_GENAI_API_KEY` - Get from https://aistudio.google.com/apikey

## Common Tasks

```bash
# Start local development
mise run dev:local

# Build everything
mise run build:functions && cd frontend && pnpm build

# Run just the frontend
cd frontend && pnpm dev

# Deploy functions
mise run deploy:functions
```
