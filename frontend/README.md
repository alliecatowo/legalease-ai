# LegalEase Frontend

Modern legal document management dashboard built with Nuxt 4, Vue 3, and Nuxt UI.

## Tech Stack

- **Framework**: Nuxt 4 with Vue 3 Composition API
- **UI**: Nuxt UI + Tailwind CSS
- **State**: VueUse composables
- **Backend**: Firebase (Auth, Firestore, Storage, Functions)
- **AI**: Genkit flows via Firebase Functions

## Quick Start

```bash
# Install dependencies
pnpm install

# Start with Firebase emulators (recommended for development)
NUXT_PUBLIC_USE_EMULATORS=true pnpm dev

# Or connect to production Firebase
pnpm dev
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required for Gemini transcription
GOOGLE_GENAI_API_KEY=your-gemini-api-key

# Firebase config (required for production, optional for emulators)
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=...
FIREBASE_PROJECT_ID=...
FIREBASE_STORAGE_BUCKET=...
FIREBASE_MESSAGING_SENDER_ID=...
FIREBASE_APP_ID=...

# Development settings
NUXT_PUBLIC_USE_EMULATORS=true  # Use Firebase emulators
TRANSCRIPTION_PROVIDER=gemini   # or 'chirp' for Google Speech API
```

## Architecture

### Composables (`app/composables/`)

Firebase-integrated composables with SSR safety:

| Composable | Purpose |
|------------|---------|
| `useAuth` | Firebase Authentication (Google sign-in) |
| `useCases` | Case CRUD operations via Firestore |
| `useDocuments` | Document upload/management via Storage + Firestore |
| `useFirestore` | Direct Firestore operations |
| `useAI` | Firebase Functions calls (transcription, summarization, search) |

All composables include `import.meta.server` guards for SSR safety.

### Key Pages

- `/` - Dashboard with case overview
- `/cases` - Case management
- `/cases/[id]` - Case detail with documents and transcripts
- `/transcriptions/[id]` - Transcript viewer with audio player
- `/search` - Semantic document search

### Firebase Integration

The app connects to Firebase services via `app/plugins/firebase.client.ts`:

- **Auth**: Google sign-in with session persistence
- **Firestore**: Real-time document database
- **Storage**: File uploads with progress tracking
- **Functions**: AI flows (transcription, summarization, search)

In development with `NUXT_PUBLIC_USE_EMULATORS=true`, services connect to local emulators. The Storage emulator connection depends on the transcription provider:
- `gemini`: Uses Storage emulator (Gemini downloads files directly)
- `chirp`: Uses production Storage (Speech API requires real GCS URIs)

## Development

```bash
# Run with hot reload
pnpm dev

# Type check
pnpm typecheck

# Lint
pnpm lint

# Build for production
pnpm build
```

## Project Structure

```
frontend/
├── app/
│   ├── components/     # Vue components
│   ├── composables/    # State management & API calls
│   ├── layouts/        # Page layouts
│   ├── pages/          # File-based routing
│   └── plugins/        # Firebase initialization
├── public/             # Static assets
└── nuxt.config.ts      # Nuxt configuration
```
