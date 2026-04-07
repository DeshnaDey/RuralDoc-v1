FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY rural_doc_env/ ./rural_doc_env/
COPY server/ ./server/
<<<<<<< HEAD
COPY rewards.py ./
COPY progression.py ./
COPY models.py ./
COPY tools.py ./
COPY scenarios/ ./scenarios/
=======
>>>>>>> bc4757869a4d0bc0fa2e82dc3c5e7c92da122024

# Expose port
EXPOSE 8000

<<<<<<< HEAD
ENV PYTHONPATH=/app

=======
>>>>>>> bc4757869a4d0bc0fa2e82dc3c5e7c92da122024
# Run the FastAPI server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
