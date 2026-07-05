FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    chromium \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN pip install browsix[cdp,serve]

EXPOSE 8080

CMD ["browsix", "serve", "--port", "8080", "--host", "0.0.0.0"]
