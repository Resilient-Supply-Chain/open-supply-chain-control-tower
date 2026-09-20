FROM node:20-alpine AS build
WORKDIR /app/Asset_UI_Team/web
COPY Asset_UI_Team/web/package*.json ./
RUN npm ci
COPY Asset_UI_Team/web/ .
RUN npm run build

FROM node:20-alpine
WORKDIR /app/Asset_UI_Team/web
COPY Asset_UI_Team/web/package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/Asset_UI_Team/web/dist ./dist
COPY --from=build /app/Asset_UI_Team/web/public ./public

# Data files (server reads from ../../../data relative to dist/)
WORKDIR /app
COPY data/input/signals/ ./data/input/signals/
COPY data/input/highways.json ./data/input/highways.json
COPY data/output/ui_output_template.json ./data/output/ui_output_template.json

WORKDIR /app/Asset_UI_Team/web
EXPOSE 3000
CMD ["node", "dist/server.js"]
