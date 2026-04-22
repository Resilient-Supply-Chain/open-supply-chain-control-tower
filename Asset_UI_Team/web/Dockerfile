# Build context: repository root.
# Build:  docker build -f Asset_UI_Team/web/Dockerfile -t osct-web .
# Run:    docker run --rm -p 3000:3000 osct-web

FROM node:20-alpine AS build
WORKDIR /app
COPY Asset_UI_Team/web/package*.json ./
RUN npm ci
COPY Asset_UI_Team/web/ ./
RUN npm run build

FROM node:20-alpine
WORKDIR /app

# App runtime (expects server at /app/dist/server.js with data at /data).
COPY Asset_UI_Team/web/package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
COPY --from=build /app/public ./public

# Data expected by the server.  server.ts resolves paths relative to
# dist/server.js via "../../../data/...", so we mirror that layout:
#   /app/dist/server.js  ->  /data/input/...
# by placing /data three levels up from dist/server.js => at the root.
COPY data /data

EXPOSE 3000
CMD ["node", "dist/server.js"]
