FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make scripts executable
RUN chmod +x start.sh wait-for-db.sh 2>/dev/null || true

# Expose port
EXPOSE 8000

# Use start script
CMD ["sh", "-c", "python manage.py migrate && python manage.py ingest_data && python manage.py runserver 0.0.0.0:8000"]

