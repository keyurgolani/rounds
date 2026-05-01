# Production build: compile the Vite SPA, then serve it from nginx
# with a small reverse-proxy layer that routes /pb/* to PocketBase and
# the runner endpoints to the FastAPI code runner. One container on
# port 80 fronts the whole app.

FROM node:20-alpine AS builder
WORKDIR /app
ARG VITE_DISABLE_SIGNUPS=false
ARG VITE_OAUTH_GOOGLE_ENABLED=false
ARG VITE_OAUTH_GITHUB_ENABLED=false
ENV VITE_DISABLE_SIGNUPS=$VITE_DISABLE_SIGNUPS
ENV VITE_OAUTH_GOOGLE_ENABLED=$VITE_OAUTH_GOOGLE_ENABLED
ENV VITE_OAUTH_GITHUB_ENABLED=$VITE_OAUTH_GITHUB_ENABLED
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/10-runtime-config.sh /docker-entrypoint.d/10-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/10-runtime-config.sh

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
