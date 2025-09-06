FROM python:3.11

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt pyproject.toml uv.lock README.md ./

# Install dependencies using pip
RUN pip install -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/
COPY run.py ./

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "run.py","run"]