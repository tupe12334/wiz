FROM openresty/openresty:alpine

COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY lua/ /etc/nginx/lua/
COPY dlp-rules/ /etc/nginx/dlp-rules/

EXPOSE 80
