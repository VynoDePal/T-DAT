#!/bin/bash

# Script de diagnostic pour CRYPTO VIZ
# Vérifie tous les prérequis et l'état du système

echo "========================================="
echo "CRYPTO VIZ - Diagnostic Système"
echo "========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

check_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

section() {
    echo ""
    echo -e "${BLUE}━━━ $1 ━━━${NC}"
}

# Fonction pour vérifier un port
check_port() {
    local port=$1
    local name=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        check_warn "$name utilise le port $port (peut causer des conflits)"
        return 1
    else
        check_ok "Port $port disponible pour $name"
        return 0
    fi
}

# 1. Vérifier Python
section "Python"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        check_ok "Python $PYTHON_VERSION (>= 3.11 requis)"
    else
        check_fail "Python $PYTHON_VERSION trouvé, mais >= 3.11 requis"
    fi
else
    check_fail "Python 3 non trouvé"
fi

# 2. Vérifier pip
if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version 2>&1 | awk '{print $2}')
    check_ok "pip $PIP_VERSION"
else
    check_fail "pip3 non trouvé"
fi

# 3. Vérifier Java
section "Java (pour Spark)"
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    check_ok "Java trouvé: $JAVA_VERSION"
    
    # Vérifier JAVA_HOME
    if [ -n "$JAVA_HOME" ]; then
        check_ok "JAVA_HOME défini: $JAVA_HOME"
    else
        check_warn "JAVA_HOME non défini (peut causer des problèmes)"
    fi
else
    check_fail "Java non trouvé (requis pour Spark)"
fi

# 4. Vérifier Docker
section "Docker"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version 2>&1 | awk '{print $3}' | tr -d ',')
    check_ok "Docker $DOCKER_VERSION"
    
    # Vérifier si Docker est en cours d'exécution
    if docker ps &> /dev/null; then
        check_ok "Docker daemon en cours d'exécution"
        
        # Vérifier les conteneurs CRYPTO VIZ
        if docker ps | grep -q t-dat-timescaledb-1; then
            check_ok "TimescaleDB conteneur actif"
        else
            check_warn "TimescaleDB conteneur non trouvé"
        fi
        
        if docker ps | grep -q t-dat-redis-1; then
            check_ok "Redis conteneur actif"
        else
            check_warn "Redis conteneur non trouvé"
        fi
    else
        check_fail "Docker daemon non accessible (sudo requis ou non démarré)"
    fi
else
    check_fail "Docker non trouvé"
fi

# 5. Vérifier Docker Compose
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short 2>&1)
    check_ok "Docker Compose (V2) $COMPOSE_VERSION"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version 2>&1 | awk '{print $4}' | tr -d ',')
    check_ok "Docker Compose (V1) $COMPOSE_VERSION"
    check_warn "Docker Compose V1 détecté, considérez de migrer vers V2 (intégré dans Docker)"
else
    check_fail "Docker Compose non trouvé"
fi

# 6. Vérifier les ports
section "Disponibilité des Ports"
check_port 15432 "TimescaleDB (Docker)"
check_port 6380 "Redis (Docker)"
check_port 8000 "Django API"

# 7. Vérifier la connectivité Kafka
section "Connectivité Kafka"
KAFKA_HOST="20.199.136.163"
KAFKA_PORT="9092"

if nc -zv $KAFKA_HOST $KAFKA_PORT 2>&1 | grep -q succeeded; then
    check_ok "Kafka accessible sur $KAFKA_HOST:$KAFKA_PORT"
elif timeout 3 bash -c "cat < /dev/null > /dev/tcp/$KAFKA_HOST/$KAFKA_PORT" 2>/dev/null; then
    check_ok "Kafka accessible sur $KAFKA_HOST:$KAFKA_PORT"
else
    check_fail "Kafka inaccessible sur $KAFKA_HOST:$KAFKA_PORT (firewall/VPN?)"
fi

# 8. Vérifier les fichiers du projet
section "Fichiers du Projet"
cd "$(dirname "$0")/.."

if [ -f ".env" ]; then
    check_ok "Fichier .env trouvé"
else
    check_warn "Fichier .env non trouvé (exécuter: cp .env.example .env)"
fi

if [ -f "docker-compose.yml" ]; then
    check_ok "docker-compose.yml trouvé"
else
    check_fail "docker-compose.yml non trouvé"
fi

# 9. Vérifier les environnements virtuels
section "Environnements Virtuels Python"
if [ -d "crypto_viz_backend/venv" ]; then
    check_ok "Environnement virtuel Django trouvé"
    
    # Vérifier les dépendances installées
    if [ -f "crypto_viz_backend/venv/bin/django-admin" ]; then
        check_ok "Django installé dans venv"
    else
        check_warn "Django non installé dans venv"
    fi
else
    check_warn "Environnement virtuel Django non trouvé"
fi

if [ -d "spark_jobs/venv" ]; then
    check_ok "Environnement virtuel Spark trouvé"
else
    check_warn "Environnement virtuel Spark non trouvé"
fi

# 10. Vérifier l'API Django
section "API Django"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health/ 2>/dev/null | grep -q 200; then
    check_ok "API Django accessible et répond (http://localhost:8000)"
else
    check_warn "API Django non accessible (peut-être pas démarrée)"
fi

# 11. Vérifier TimescaleDB
section "TimescaleDB"
if docker ps | grep -q t-dat-timescaledb-1; then
    if docker exec t-dat-timescaledb-1 pg_isready -U postgres &>/dev/null; then
        check_ok "TimescaleDB prête à accepter des connexions"
    else
        check_warn "TimescaleDB en cours de démarrage"
    fi
fi

# 12. Vérifier les processus
section "Processus en Cours"
if ps aux | grep -v grep | grep "manage.py runserver" > /dev/null; then
    check_ok "Serveur Django en cours d'exécution"
else
    check_warn "Serveur Django non trouvé"
fi

if ps aux | grep -v grep | grep "kafka_to_timescale.py" > /dev/null; then
    check_ok "Job Spark Ingestion en cours d'exécution"
else
    check_warn "Job Spark Ingestion non trouvé"
fi

if ps aux | grep -v grep | grep "sentiment_prediction_job.py" > /dev/null; then
    check_ok "Job Spark Analytics en cours d'exécution"
else
    check_warn "Job Spark Analytics non trouvé"
fi

# 13. Vérifier l'espace disque
section "Espace Disque"
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_ok "Espace disque : ${DISK_USAGE}% utilisé"
elif [ "$DISK_USAGE" -lt 90 ]; then
    check_warn "Espace disque : ${DISK_USAGE}% utilisé (attention)"
else
    check_fail "Espace disque : ${DISK_USAGE}% utilisé (critique!)"
fi

# 14. Vérifier la mémoire
section "Mémoire RAM"
if command -v free &> /dev/null; then
    MEM_AVAILABLE=$(free -m | awk 'NR==2 {print $7}')
    if [ "$MEM_AVAILABLE" -gt 2000 ]; then
        check_ok "Mémoire disponible : ${MEM_AVAILABLE}MB"
    elif [ "$MEM_AVAILABLE" -gt 1000 ]; then
        check_warn "Mémoire disponible : ${MEM_AVAILABLE}MB (limité)"
    else
        check_fail "Mémoire disponible : ${MEM_AVAILABLE}MB (insuffisant!)"
    fi
fi

# Résumé
echo ""
echo "========================================="
echo "Résumé du Diagnostic"
echo "========================================="
echo ""
echo "Pour démarrer le projet:"
echo "  ./scripts/setup_project.sh    # Installation"
echo "  ./scripts/start_all.sh         # Démarrage"
echo ""
echo "Pour tester les connexions:"
echo "  python3 scripts/test_kafka_connection.py"
echo "  python3 scripts/test_timescale_connection.py"
echo ""
echo "Pour voir les logs:"
echo "  tail -f logs/django.log"
echo "  tail -f logs/spark_ingestion.log"
echo ""
echo "Pour plus d'aide, consultez:"
echo "  - README.md"
echo "  - TROUBLESHOOTING.md"
echo ""
