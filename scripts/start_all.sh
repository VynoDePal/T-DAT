#!/bin/bash

# Script pour démarrer tous les composants de CRYPTO VIZ

set -e

echo "========================================="
echo "CRYPTO VIZ - Démarrage Complet"
echo "========================================="
echo ""

# Déterminer le répertoire du projet (parent du répertoire scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier que les fichiers .env existent
if [ ! -f "$PROJECT_DIR/.env" ]; then
    log_warn "Fichier .env non trouvé, création depuis .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    log_info ".env créé avec succès"
fi

# Fonction pour vérifier et libérer les ports
check_and_free_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        log_warn "Port $port déjà utilisé par un service local"
        
        # Essayer d'arrêter le service système
        if systemctl is-active --quiet $service_name 2>/dev/null; then
            log_info "Arrêt du service système $service_name..."
            sudo systemctl stop $service_name
            sleep 2
        else
            log_error "Port $port occupé. Veuillez libérer le port manuellement :"
            echo "  sudo lsof -i :$port"
            echo "  sudo systemctl stop $service_name"
            exit 1
        fi
    fi
}

# Note: Les ports Docker sont mappés sur 15432 et 6380 pour éviter les conflits
# Pas besoin de vérifier les ports car on utilise des ports alternatifs

# 1. Démarrer Zookeeper, Kafka, TimescaleDB et Redis avec Docker
log_info "Démarrage des services Docker (Zookeeper, Kafka, TimescaleDB, Redis, Monitoring)..."
cd "$PROJECT_DIR"
docker compose up -d

log_info "Attente du démarrage des services (40s pour stabilisation Kafka)..."
sleep 40

# 2. Créer les topics Kafka
log_info "Création des topics Kafka..."
"$PROJECT_DIR/scripts/create_kafka_topics.sh" || log_error "Échec de la création des topics Kafka"

# 3. Initialiser la base de données TimescaleDB
log_info "Initialisation de TimescaleDB..."
docker exec -i crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts < "$PROJECT_DIR/database/timescaledb_setup.sql" 2>/dev/null || log_warn "Tables déjà créées"

# 4. Backend Django déjà démarré par Docker Compose
log_info "✓ Backend Django démarré via Docker Compose"

# 5. Démarrer les jobs Spark
log_info "Démarrage des jobs Spark..."
cd "$PROJECT_DIR/spark_jobs"

if [ ! -d "venv" ]; then
    log_info "Création de l'environnement virtuel pour Spark..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

log_info "Démarrage du job d'ingestion Spark..."
nohup python kafka_to_timescale.py > "$PROJECT_DIR/logs/spark_ingestion.log" 2>&1 &
SPARK_INGEST_PID=$!
echo $SPARK_INGEST_PID > "$PROJECT_DIR/logs/spark_ingestion.pid"

log_info "Démarrage du job d'analytics Spark..."
nohup python sentiment_prediction_job.py > "$PROJECT_DIR/logs/spark_analytics.log" 2>&1 &
SPARK_ANALYTICS_PID=$!
echo $SPARK_ANALYTICS_PID > "$PROJECT_DIR/logs/spark_analytics.pid"

cd "$PROJECT_DIR"

echo ""
echo "========================================="
echo -e "${GREEN}✓ Tous les services sont démarrés!${NC}"
echo "========================================="
echo ""
echo "Services Docker actifs:"
echo "  - Zookeeper:          port 2181, 7072 (JMX)"
echo "  - Kafka:              port 9092, 7071 (JMX)"
echo "  - TimescaleDB:        port 15432"
echo "  - Redis:              port 6380"
echo "  - Django API:         port 8000"
echo "  - Prometheus:         port 9090"
echo "  - Grafana:            port 3000"
echo "  - Kafka Exporter:     port 9308"
echo "  - Node Exporter:      port 9100"
echo "  - Redis Exporter:     port 9121"
echo "  - Postgres Exporter:  port 9187"
echo ""
echo "Services Spark (PIDs):"
echo "  - Spark Ingestion:  PID $SPARK_INGEST_PID"
echo "  - Spark Analytics:  PID $SPARK_ANALYTICS_PID"
echo ""
echo "URLs principales:"
echo "  🌐 Django API:    http://localhost:8000/api/v1/"
echo "  🔐 Admin Django:  http://localhost:8000/admin/ (admin/admin)"
echo "  💚 Health Check:  http://localhost:8000/api/v1/health/"
echo "  📊 Prometheus:    http://localhost:9090"
echo "  📈 Grafana:       http://localhost:3000 (admin/admin)"
echo ""
echo "Logs:"
echo "  - Spark Ingest:    tail -f logs/spark_ingestion.log"
echo "  - Spark Analytics: tail -f logs/spark_analytics.log"
echo "  - Docker:          docker logs crypto_viz_kafka"
echo ""
echo "Commandes utiles:"
echo "  - Arrêter tout:     ./scripts/stop_all.sh"
echo "  - Topics Kafka:     docker exec crypto_viz_kafka kafka-topics --bootstrap-server kafka:29092 --list"
echo "  - Containers:       docker ps"
echo ""
