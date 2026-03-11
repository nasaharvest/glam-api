FROM python:3.11.10-slim-bullseye

WORKDIR /app

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install GDAL and other geospatial libraries
RUN apt-get update && apt-get install -y binutils build-essential libgdal-dev libproj-dev gdal-bin libsqlite3-mod-spatialite 

# Install pip requirements
COPY pyproject.toml .
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install
# Force no-binary rasterio install via pip with setuptools available
RUN pip uninstall -y rasterio
RUN pip install --upgrade setuptools wheel
RUN pip install rasterio==1.3.11 --no-binary rasterio --no-cache-dir

# Copy project files
COPY . .

CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "--chdir", "glam_api", "config.wsgi:application"]
