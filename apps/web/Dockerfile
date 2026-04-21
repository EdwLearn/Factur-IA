FROM node:20-alpine AS builder
WORKDIR /app

# shared-types already has dist/ built — copy it as a local file dep
COPY packages/shared-types ./packages/shared-types

# Copy web source
COPY apps/web/ ./apps/web/

WORKDIR /app/apps/web

# Patch package.json:
#   - workspace:* → file:../../packages/shared-types (npm doesn't understand workspace: protocol)
#   - remove @facturia/eslint-config (ESLint is disabled during build, saves ~50 packages)
# Patch package.json for Docker:
#   1. Replace workspace:* with local file path (npm doesn't understand workspace: protocol)
#   2. Remove test-only devDeps — not needed for `next build` and cause network timeouts
RUN node -e "const fs=require('fs');const p=JSON.parse(fs.readFileSync('package.json','utf8'));p.dependencies['@facturia/shared-types']='file:../../packages/shared-types';['@facturia/eslint-config','@playwright/test','@testing-library/jest-dom','@testing-library/react','@testing-library/user-event','vitest','jsdom','@vitejs/plugin-react'].forEach(d=>delete p.devDependencies[d]);fs.writeFileSync('package.json',JSON.stringify(p,null,2));"

# npm install (no lockfile — package.json was patched, lockfile no longer matches)
# NOTE: local Docker build on WSL2 requires --network=host flag to avoid MTU timeouts:
#   docker build --network=host -t facturia-web -f apps/web/Dockerfile .
# Railway's network is stable — no special flag needed there.
RUN npm install --legacy-peer-deps

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
RUN corepack disable

COPY --from=builder /app/apps/web/public ./public
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./.next/static

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
