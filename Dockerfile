FROM python:3.11-slim-bullseye

WORKDIR /app

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY pyproject.toml .
RUN python -m pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

# Install GDAL and other geospatial libraries
RUN apt-get update && apt-get install -y binutils libproj-dev gdal-bin libsqlite3-mod-spatialite 

# Copy project files
COPY . .

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "--chdir", "glam_api", "config.wsgi:application"]
