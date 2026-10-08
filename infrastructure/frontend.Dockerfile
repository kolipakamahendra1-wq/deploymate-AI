FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine
# The nginx image renders /etc/nginx/templates/*.template with these variables at start-up.
ENV PORT=80 BACKEND_URL=http://backend:8000 NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1
COPY infrastructure/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
