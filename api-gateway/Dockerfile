FROM nginx:alpine

RUN apk add --no-cache gettext

COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.d/99-yana-gateway-envsubst.sh
COPY demo /usr/share/nginx/html/demo
