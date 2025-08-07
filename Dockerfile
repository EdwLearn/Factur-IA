# Multi-stage build: Primero construir el frontend
FROM node:18-alpine as frontend-builder

WORKDIR /app

# Copiar todo el contexto primero
COPY . .

# Instalar y construir frontend (usar build, no dev)
RUN cd apps/web && npm install && npm run build

# Stage principal: Backend con Python
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
WORKDIR /app

# Copia todo el contexto
COPY . .

# Instala dependencias de Python desde la raíz (donde está requirements.txt)
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia el frontend construido desde la etapa anterior
COPY --from=frontend-builder /app/apps/web/.next ./apps/web/.next
COPY --from=frontend-builder /app/apps/web/public ./apps/web/public

# Variables de entorno
ENV PYTHONPATH=/app

# Expone el puerto
EXPOSE 8000

# Comando para iniciar el servidor
CMD ["uvicorn", "apps.api.src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]