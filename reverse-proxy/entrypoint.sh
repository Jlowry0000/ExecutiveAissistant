#!/bin/sh
set -e

mkdir -p /etc/nginx/ssl

if [ ! -f /etc/nginx/ssl/cert.pem ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/key.pem \
        -out /etc/nginx/ssl/cert.pem \
        -subj "/CN=${NGINX_SERVER_NAME:-localhost}" \
        -addext "subjectAltName=DNS:${NGINX_SERVER_NAME:-localhost},DNS:localhost,IP:127.0.0.1"
fi

exec nginx -g 'daemon off;'
