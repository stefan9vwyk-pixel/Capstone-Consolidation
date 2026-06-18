# 1. Use the official Python base image
FROM python:3.12-slim

# 2. Set environment variables to optimize Python inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. INSTALL SYSTEM DEPENDENCIES FOR MYSQLCLIENT
# We clean up the package index cache afterward to keep the image slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Set the working directory inside the container
WORKDIR /app/news_project

# 5. Copy the requirements file first
COPY requirements.txt /app/

# 6. Install the project dependencies (this will now succeed)
RUN pip install --no-cache-dir -r /app/requirements.txt

# 7. Copy the rest of your application code
COPY . /app/

# 8. Expose the port that Django runs on
EXPOSE 8000

# 9. Start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
