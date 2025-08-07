# Multi-stage build: Primero construir el frontend
FROM node:18-alpine as frontend-builder

WORKDIR /app

# Copiar archivos del frontend
COPY apps/web/package*.json apps/web/
RUN cd apps/web && npm install

# Copiar código y construir
COPY apps/web/ apps/web/
RUN cd apps/web && npm run build

# Stage principal: Backend con Python
FROM python:3.11-slim

# Instala dependencias del sistema necesarias para opencv, fonts y demás
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
WORKDIR /app

# Copia archivos del backend
COPY apps/api/requirements.txt .
COPY apps/api/ .

# Instala dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia el frontend construido desde la etapa anterior
COPY --from=frontend-builder /app/apps/web/.next ./apps/web/.next
COPY --from=frontend-builder /app/apps/web/public ./apps/web/public
COPY --from=frontend-builder /app/apps/web/package.json ./apps/web/

# Variables de entorno
ENV PYTHONPATH=/app

# Expone el puerto
EXPOSE 8000

# Comando para iniciar el servidor
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]