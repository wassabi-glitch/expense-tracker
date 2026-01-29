# 1. Use Python 3.12 as the base
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Set environment variables
# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures logs are sent straight to the terminal
ENV PYTHONUNBUFFERED 1

# 4. Install system dependencies
# We need 'libpq-dev' and 'gcc' so the 'psycopg2' library can talk to Postgres
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the entire project into the container
COPY . .

# 7. The command to run the app
# We use uvicorn to serve the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]