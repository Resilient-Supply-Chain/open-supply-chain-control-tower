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

# App runtime (server at /app/dist/server.js, static assets at /app/public).
COPY Asset_UI_Team/web/package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
COPY --from=build /app/public ./public

# server.ts resolves data as "../../../data/..." relative to dist/server.js,
# which lands at /data.  Copy only the files the server actually reads rather
# than the whole data/ tree (which carries ~3.4 MB of archived reports).
COPY data/input/signals/ /data/input/signals/
COPY data/input/highways.json /data/input/highways.json
COPY data/input/registered_provider/ /data/input/registered_provider/
COPY data/output/ui_output_template.json /data/output/ui_output_template.json

EXPOSE 3000
CMD ["node", "dist/server.js"]
