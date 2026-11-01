ARG NODE_BASE_IMAGE=node:24-alpine
ARG NGINX_BASE_IMAGE=nginx:1.29-alpine

FROM ${NODE_BASE_IMAGE} AS build
ARG NPM_REGISTRY=https://registry.npmjs.org

WORKDIR /app

COPY frontend/package*.json ./
RUN npm config set registry ${NPM_REGISTRY} \
    && npm ci

COPY frontend/ ./
RUN npm run build

FROM ${NGINX_BASE_IMAGE}

COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
