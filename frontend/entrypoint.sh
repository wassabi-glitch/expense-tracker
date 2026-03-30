#!/bin/sh
# --- FINAL DEBUG START ---
echo "--- CURRENT NGINX CONFIG ---"
cat /etc/nginx/conf.d/default.conf

# Manual replacement of industry-grade symbols
# Using | as a delimiter for safety
sed -i "s|__REPLACE_ME_WITH_API_URL__|$API_URL|g" /etc/nginx/conf.d/default.conf
sed -i "s|__REPLACE_ME_WITH_API_HOST__|$API_HOST|g" /etc/nginx/conf.d/default.conf

echo "--- MODIFIED NGINX CONFIG ---"
cat /etc/nginx/conf.d/default.conf
echo "--- END DEBUG ---"

# Start Nginx
exec nginx -g 'daemon off;'
