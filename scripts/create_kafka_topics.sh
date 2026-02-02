#!/bin/bash

# Script pour créer automatiquement les topics Kafka nécessaires
# Inspiré de T-DAT-1 : https://github.com/Izzoudine/T-DAT-1

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Création des Topics Kafka"
echo "========================================="
echo ""

# Attendre que Kafka soit prêt
echo -e "${YELLOW}[INFO]${NC} Attente de la disponibilité de Kafka..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec t-dat-kafka-1 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server kafka:29092 &> /dev/null; then
        echo -e "${GREEN}✓${NC} Kafka est prêt!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}[INFO]${NC} Tentative $RETRY_COUNT/$MAX_RETRIES - En attente..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗${NC} Kafka n'a pas démarré dans le temps imparti"
    exit 1
fi

echo ""
echo "========================================="
echo "Création des Topics"
echo "========================================="
echo ""

# Configuration des topics avec optimisations
REPLICATION_FACTOR=1

# Fonction pour créer un topic avec configuration optimisée
create_optimized_topic() {
    local TOPIC=$1
    local PARTITIONS=$2
    local RETENTION_MS=$3
    local SEGMENT_BYTES=$4
    
    echo -e "${YELLOW}[INFO]${NC} Création du topic optimisé: $TOPIC"
    
    docker exec t-dat-kafka-1 /opt/kafka/bin/kafka-topics.sh \
        --bootstrap-server kafka:29092 \
        --create \
        --topic "$TOPIC" \
        --partitions $PARTITIONS \
        --replication-factor $REPLICATION_FACTOR \
        --config compression.type=lz4 \
        --config retention.ms=$RETENTION_MS \
        --config segment.bytes=$SEGMENT_BYTES \
        --config min.insync.replicas=1 \
        --config max.message.bytes=10485760 \
        --if-not-exists 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Topic $TOPIC configuré avec succès"
    fi
}

# Créer les topics avec configurations spécifiques
# rawticker: haute fréquence, rétention 7 jours, segments 512MB
echo -e "${YELLOW}[INFO]${NC} Configuration rawticker: 6 partitions, 7j rétention"
create_optimized_topic "rawticker" 6 604800000 536870912

# rawtrade: très haute fréquence, rétention 3 jours, segments 512MB
echo -e "${YELLOW}[INFO]${NC} Configuration rawtrade: 6 partitions, 3j rétention"
create_optimized_topic "rawtrade" 6 259200000 536870912

# rawarticle: basse fréquence, rétention 30 jours, segments 128MB
echo -e "${YELLOW}[INFO]${NC} Configuration rawarticle: 3 partitions, 30j rétention"
create_optimized_topic "rawarticle" 3 2592000000 134217728

# rawalert: moyenne fréquence, rétention 14 jours, segments 256MB
echo -e "${YELLOW}[INFO]${NC} Configuration rawalert: 3 partitions, 14j rétention"
create_optimized_topic "rawalert" 3 1209600000 268435456

echo ""
echo "========================================="
echo "Vérification des Topics"
echo "========================================="
echo ""

# Lister tous les topics
echo -e "${YELLOW}[INFO]${NC} Topics disponibles:"
docker exec t-dat-kafka-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:29092 --list

echo ""
echo -e "${GREEN}✓✓✓${NC} Tous les topics Kafka sont prêts!"
echo ""
