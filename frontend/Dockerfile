FROM node:22-alpine AS build

WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NODE_OPTIONS=--max-old-space-size=768
RUN npm run build-only

FROM nginx:1.27-alpine
COPY deploy/nginx.docker.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
