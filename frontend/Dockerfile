# ─────────────────────────────────────────────────────────────────────────────
# EpitopX AI — Frontend Dockerfile
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

RUN addgroup -S epitopx && adduser -S epitopx -G epitopx

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --chown=epitopx:epitopx . .

USER epitopx

EXPOSE 3333

ENV NODE_ENV=production \
    PORT=3333

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3333/api/_status', r => process.exit(r.statusCode === 200 ? 0 : 1))"

CMD ["node", "server.js"]
