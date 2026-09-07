# StudioOps frontend — Next.js 14 (App Router) on Cloud Run.
#
# Build from the frontend/ directory:
#   docker build -f frontend/Dockerfile -t studioops-web ./frontend
#
# NEXT_PUBLIC_* values are baked in at build time, so pass the backend URL as a
# build arg when the browser calls Cloud Run directly:
#   docker build --build-arg NEXT_PUBLIC_API_BASE_URL=https://studioops-api-... ./frontend

# --- deps: install once, cached on package.json changes --------------------
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# --- builder: compile the standalone server bundle -------------------------
FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Bake the public API base URL (empty by default → same-origin via rewrites).
ARG NEXT_PUBLIC_API_BASE_URL=""
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# --- runner: minimal image, standalone output only ------------------------
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN groupadd --system --gid 1001 nodejs \
    && useradd --system --uid 1001 --gid nodejs nextjs

# The standalone output bundles a minimal server + only the deps it uses.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

# Cloud Run injects $PORT; Next's standalone server reads PORT and HOSTNAME.
ENV PORT=8080 \
    HOSTNAME=0.0.0.0
EXPOSE 8080

# When BACKEND_ORIGIN is set, next.config rewrites /api and /reports to it at
# runtime, so the frontend and backend can share one public origin.
CMD ["node", "server.js"]
