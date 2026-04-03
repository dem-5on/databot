FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (minimal - no PostgreSQL client needed)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --upgrade pip

# Copy application code
COPY . .

# Add app directory to Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Make entrypoint script executable
RUN chmod +x ./app/entrypoint.sh

# Expose port
EXPOSE 8000

# Use entrypoint script
CMD ["./app/entrypoint.sh"]

