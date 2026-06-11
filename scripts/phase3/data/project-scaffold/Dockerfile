# syntax=docker/dockerfile:1.6
FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

COPY package.json pnpm-workspace.yaml .npmrc tsconfig.base.json eslint.config.mjs vitest.config.ts ./
COPY apps/api/package.json apps/api/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
COPY packages/api-client/package.json packages/api-client/package.json
RUN --mount=type=cache,id=phase3-pnpm-store,target=/pnpm/store pnpm install --frozen-lockfile=false --store-dir /pnpm/store

FROM deps AS api-builder
COPY apps/api ./apps/api
COPY packages ./packages
COPY db ./db
COPY tests ./tests
RUN pnpm --filter @app/api build

FROM deps AS web-builder
COPY apps/web ./apps/web
COPY packages ./packages
RUN pnpm --filter @app/web build

FROM node:20-alpine AS web-runtime
WORKDIR /app
RUN addgroup -S nodeapp && adduser -S nodeapp -G nodeapp
RUN corepack enable
COPY --from=web-builder --chown=nodeapp:nodeapp /app /app
ENV CONTAINER_HEALTH_PORT=3100
ENV CONTAINER_HEALTH_PATH=/
USER nodeapp
EXPOSE 3100
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 CMD wget -q -O - "http://127.0.0.1:${CONTAINER_HEALTH_PORT}${CONTAINER_HEALTH_PATH}" >/dev/null 2>&1 || exit 1
CMD ["pnpm", "--filter", "@app/web", "start"]

FROM node:20-alpine AS runtime
WORKDIR /app
RUN addgroup -S nodeapp && adduser -S nodeapp -G nodeapp
RUN corepack enable
COPY --from=api-builder --chown=nodeapp:nodeapp /app /app
ENV CONTAINER_HEALTH_PORT=3000
ENV CONTAINER_HEALTH_PATH=/healthz
USER nodeapp
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 CMD wget -q -O - "http://127.0.0.1:${CONTAINER_HEALTH_PORT}${CONTAINER_HEALTH_PATH}" >/dev/null 2>&1 || exit 1
CMD ["pnpm", "--filter", "@app/api", "start:container"]
