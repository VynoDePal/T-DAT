#!/bin/bash

# Script pour démarrer tous les producteurs de données

set -e

echo "========================================="
echo "🚀 Démarrage des Producteurs Kafka"
echo "========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

cd "$(dirname "$0")"

# Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    log_info "Création de l'environnement virtuel Python..."
    python3 -m venv venv
fi

source venv/bin/activate

# Installer les dépendances
log_info "Installation des dépendances..."
pip install -q -r requirements.txt

# Créer le dossier logs
mkdir -p ../logs

# Vérifier que Kafka est accessible
log_info "Vérification de la connexion Kafka..."
if ! nc -zv localhost 9092 2>&1 | grep -q "succeeded"; then
    log_warn "Kafka n'est pas accessible sur localhost:9092"
    log_warn "Assurez-vous que Kafka est démarré: ./scripts/start_all.sh"
    exit 1
fi

log_info "✅ Kafka est accessible"
echo ""

# Démarrer le producteur Kraken
log_info "Démarrage du producteur Kraken (WebSocket)..."
nohup python3 -u kraken_producer.py > ../logs/kraken_producer.log 2>&1 &
KRAKEN_PID=$!
echo $KRAKEN_PID > ../logs/kraken_producer.pid
log_info "✅ Producteur Kraken démarré (PID: $KRAKEN_PID)"

# Attendre un peu pour la stabilisation
sleep 2

# Démarrer le scraper d'articles
log_info "Démarrage du scraper d'articles crypto..."
nohup python3 -u article_scraper.py > ../logs/article_scraper.log 2>&1 &
ARTICLE_PID=$!
echo $ARTICLE_PID > ../logs/article_scraper.pid
log_info "✅ Scraper d'articles démarré (PID: $ARTICLE_PID)"

echo ""
echo "========================================="
echo -e "${GREEN}✓ Tous les producteurs sont démarrés!${NC}"
echo "========================================="
echo ""
echo "Producteurs actifs:"
echo "  - Kraken WebSocket:  PID $KRAKEN_PID (rawticker, rawtrade, rawalert)"
echo "  - Article Scraper:   PID $ARTICLE_PID (rawarticle)"
echo ""
echo "Logs:"
echo "  - Kraken:   tail -f logs/kraken_producer.log"
echo "  - Articles: tail -f logs/article_scraper.log"
echo ""
echo "Pour arrêter: ./data_producers/stop_producers.sh"
echo ""
