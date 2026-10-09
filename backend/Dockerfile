FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
COPY index.html styles.css app.js thanks.html admin.html admin.js /app/static/
ENV PYTHONPATH=/app
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8000"]
