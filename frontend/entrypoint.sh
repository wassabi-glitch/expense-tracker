#!/bin/sh
# BUILD ID: 1774825109354 - GHOST BUSTER 3000
echo "--- DEBUG: Current Nginx Config ---"
cat /etc/nginx/conf.d/default.conf
echo "--- END DEBUG ---"

# Manual replacement of placeholders
# We use | as a delimiter because the URL contains /
sed -i "s|__API_URL__|$API_URL|g" /etc/nginx/conf.d/default.conf
sed -i "s|__API_HOST__|$API_HOST|g" /etc/nginx/conf.d/default.conf

echo "--- DEBUG: Modified Nginx Config ---"
cat /etc/nginx/conf.d/default.conf
echo "--- END DEBUG ---"

exec nginx -g 'daemon off;'
