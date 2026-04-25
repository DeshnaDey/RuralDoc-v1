FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all packages (paths relative to repo root — build with: docker build -f backend/Dockerfile .)
COPY backend/  ./backend/
COPY db/       ./db/
COPY env/      ./env/
COPY models/   ./models/
COPY rag/      ./rag/

# Expose HuggingFace Spaces default port
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
