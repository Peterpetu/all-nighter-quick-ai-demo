# Python runtime as a parent image
FROM python:3.11.2-slim

# Prevent Python from writing .pyc files and buffer flushing
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Poetry
RUN pip install poetry

# Working directory
WORKDIR /app

# Copy only dependency descriptors for caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies, no root package
RUN poetry install --no-interaction --no-ansi --no-root

COPY . .

# The port Uvicorn will listen
EXPOSE 8000

# Run with Poetry’s venv
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
