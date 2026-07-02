FROM python:3.11-alpine

RUN apk add --no-cache postgresql-client curl bash \
    && curl -fsSL -o /usr/local/bin/kubectl \
       "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')/kubectl" \
    && chmod +x /usr/local/bin/kubectl

CMD ["sleep", "infinity"]
