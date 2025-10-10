# Base stage with Node.js 22
FROM node:22-alpine AS base

# Install pnpm globally
RUN corepack enable && corepack prepare pnpm@latest --activate

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/pnpm-lock.yaml* ./

# Development stage
FROM base AS development

# Install all dependencies including devDependencies
RUN pnpm install --frozen-lockfile

# Copy application code
COPY frontend/ ./

# Expose Nuxt dev server port
EXPOSE 3000

# Start development server
CMD ["pnpm", "dev"]

# Dependencies stage for production
FROM base AS dependencies

# Install production dependencies only
RUN pnpm install --frozen-lockfile --prod

# Build stage
FROM base AS build

# Install all dependencies for building
RUN pnpm install --frozen-lockfile

# Copy application code
COPY frontend/ ./

# Build the application
RUN pnpm build

# Production stage
FROM node:22-alpine AS production

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy built application and dependencies
COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=build /app/.output ./.output
COPY --from=build /app/package.json ./package.json

# Set production environment
ENV NODE_ENV=production

# Expose production port
EXPOSE 3000

# Start the production server
CMD ["node", ".output/server/index.mjs"]
