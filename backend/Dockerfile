FROM python:3.11-slim

RUN useradd --create-home appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

# --proxy-headers with --forwarded-allow-ips=* trusts X-Forwarded-For/-Proto from any
# peer. That is only safe because Fly's proxy is the sole way in to this machine;
# do not run this image with the port exposed directly. (WebSocket per-message
# deflate is on by default, so no flag is needed for it.)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
