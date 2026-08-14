FROM node:22.23.1-alpine@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2 AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm ci --workspace @biaice/web --ignore-scripts

FROM node:22.23.1-alpine@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2 AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 NODE_ENV=production
COPY --from=dependencies /app/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY apps/web/ ./apps/web/
RUN npm run build --workspace @biaice/web

FROM node:22.23.1-alpine@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2 AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
RUN addgroup --system --gid 10001 biaice \
    && adduser --system --uid 10001 --ingroup biaice biaice
COPY --from=builder --chown=biaice:biaice /app/apps/web/.next/standalone ./
COPY --from=builder --chown=biaice:biaice /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=biaice:biaice /app/apps/web/public ./apps/web/public
USER 10001:10001
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
