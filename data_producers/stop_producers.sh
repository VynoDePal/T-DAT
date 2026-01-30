#!/bin/bash

# Script pour arrêter tous les producteurs de données

set -e

echo "========================================="
echo "Arrêt des Producteurs Kafka"
echo "========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

cd "$(dirname "$0")/.."

# Arrêter le producteur Kraken
if [ -f "logs/kraken_producer.pid" ]; then
    KRAKEN_PID=$(cat logs/kraken_producer.pid)
    log_info "Arrêt du producteur Kraken (PID: $KRAKEN_PID)..."
    kill $KRAKEN_PID 2>/dev/null || true
    rm logs/kraken_producer.pid
fi

# Arrêter le scraper d'articles
if [ -f "logs/article_scraper.pid" ]; then
    ARTICLE_PID=$(cat logs/article_scraper.pid)
    log_info "Arrêt du scraper d'articles (PID: $ARTICLE_PID)..."
    kill $ARTICLE_PID 2>/dev/null || true
    rm logs/article_scraper.pid
fi

echo ""
echo "========================================="
echo -e "${GREEN}✓ Tous les producteurs sont arrêtés!${NC}"
echo "========================================="
echo ""
