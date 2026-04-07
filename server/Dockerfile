FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY rural_doc_env/ ./rural_doc_env/
COPY server/ ./server/
COPY rewards.py ./
COPY progression.py ./
COPY models.py ./
COPY tools.py ./
COPY scenarios/ ./scenarios/

# Expose port
EXPOSE 7860

ENV PYTHONPATH=/app

# Run the FastAPI server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
