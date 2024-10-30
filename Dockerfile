# Use Python 3.12 slim image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app/mugshoter

# Copy the current directory contents into the container at /app
COPY . /app/mugshoter

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Install pip and poetry
RUN pip install --upgrade pip && \
    pip install poetry

# Install project dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME MugshotScraper

# Run app.py when the container launches
CMD ["python", "main.py"]