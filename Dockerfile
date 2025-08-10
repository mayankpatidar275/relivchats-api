# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for psycopg2-binary and others that might be needed
# libpq-dev is for psycopg2 (PostgreSQL client library)
# build-essential and gcc are for compiling packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    git \ # Required for sentence-transformers to download models
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
# --no-cache-dir to prevent caching pip packages, reducing image size
# --compile to compile Python source files to bytecode, potentially speeding up startup
RUN pip install --no-cache-dir --compile -r requirements.txt

# Expose the port FastAPI runs on
EXPOSE 8000

# Run the application
# Use uvicorn with Gunicorn for production deployments for better performance and robustness
# We are using `app.main:app` because the FastAPI app object is named 'app' in 'app/main.py'
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]