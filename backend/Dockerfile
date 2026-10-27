FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY deploy/backend-entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && mkdir -p /app/backend/uploads

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
