#!/bin/bash

# Script pour arrêter tous les composants de CRYPTO VIZ

set -e

echo "========================================="
echo "CRYPTO VIZ - Arrêt des Services"
echo "========================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

cd "$(dirname "$0")/.."

# 1. Arrêter les jobs Spark
if [ -f "logs/spark_ingestion.pid" ]; then
    SPARK_INGEST_PID=$(cat logs/spark_ingestion.pid)
    log_info "Arrêt du job Spark Ingestion (PID: $SPARK_INGEST_PID)..."
    kill $SPARK_INGEST_PID 2>/dev/null || true
    rm logs/spark_ingestion.pid
fi

if [ -f "logs/spark_analytics.pid" ]; then
    SPARK_ANALYTICS_PID=$(cat logs/spark_analytics.pid)
    log_info "Arrêt du job Spark Analytics (PID: $SPARK_ANALYTICS_PID)..."
    kill $SPARK_ANALYTICS_PID 2>/dev/null || true
    rm logs/spark_analytics.pid
fi

# 2. Arrêter Django
if [ -f "logs/django.pid" ]; then
    DJANGO_PID=$(cat logs/django.pid)
    log_info "Arrêt du serveur Django (PID: $DJANGO_PID)..."
    kill $DJANGO_PID 2>/dev/null || true
    rm logs/django.pid
fi

# 3. Arrêter les conteneurs Docker
log_info "Arrêt de tous les services Docker (Kafka, TimescaleDB, Redis)..."
docker compose down

echo ""
echo "========================================="
echo -e "${GREEN}✓ Tous les services sont arrêtés!${NC}"
echo "========================================="
echo ""
