# syntax=docker/dockerfile:1
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
# `npm install` (not `ci`) — npm 10.9.9 inside node:22-alpine mis-resolves
# this lockfile's hoisted ajv peer dependency; install keeps builds reliable.
RUN npm install --no-audit --no-fund

COPY . .

# Empty by default: same-origin /api calls, proxied by nginx below.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
