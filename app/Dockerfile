FROM python:3.11-alpine

RUN adduser -D -h /home/appuser appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Derek's idea of "hardening": once the app is up, revoke execute permission
# on the python/pip binaries so nobody can pop a shell and run arbitrary
# python. He forgot the container still owns those files as `appuser`, so
# `appuser` can always chmod them back.
RUN chown -R appuser:appuser /usr/local/bin/python3.11 /usr/local/bin/pip* /app

USER appuser
EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
