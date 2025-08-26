# Dockerfile - Solo backend, Railway maneja el frontend
FROM python:3.11-slim

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Crea y activa el entorno virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Crea directorio de trabajo
WORKDIR /code

# Copia todo el proyecto (incluyendo frontend ya construido)
COPY . .

# Instala dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Variables de entorno
ENV PYTHONPATH=/app

# Expone el puerto
EXPOSE 8000

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Comando para iniciar el servidor
CMD ["sh", "-c", "uvicorn apps.api.src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]