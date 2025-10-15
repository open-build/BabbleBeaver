# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Download GCP credentials from Google Cloud Storage
RUN apt-get update && apt-get install -y curl && \
  curl -o /app/assets/drunr-prod-97f378603f61.json https://storage.googleapis.com/drunr_files_bucket/gcp_creds.json

# Command to run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--reload"]

# Specify tag name to be created on github
LABEL version="1.0.1"
