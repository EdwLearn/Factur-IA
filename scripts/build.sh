#!/bin/bash
# Build para producción
cd apps/api && docker build -t invoice-api .
cd apps/web && npm run build