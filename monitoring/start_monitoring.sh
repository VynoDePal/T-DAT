#!/bin/bash

# Script pour démarrer le health check monitoring

cd "$(dirname "$0")/.."

echo "================================================"
echo "🏥 Démarrage du Health Check Monitor"
echo "================================================"

# Créer le virtualenv si nécessaire
if [ ! -d "monitoring/venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv monitoring/venv
fi

# Activer et installer les dépendances
source monitoring/venv/bin/activate
pip install -q psutil requests confluent-kafka prometheus-client

# Créer le dossier de logs si nécessaire
mkdir -p logs

# Démarrer le health check monitor
echo "▶️  Démarrage du monitor..."
nohup python monitoring/health_check.py > logs/health_check.log 2>&1 &
MONITOR_PID=$!
echo $MONITOR_PID > logs/health_monitor.pid

echo "✅ Health Check Monitor démarré (PID: $MONITOR_PID)"
echo "📊 Métriques Prometheus: http://localhost:9999/metrics"
echo "📝 Logs: tail -f logs/health_check.log"
echo "🚨 Alertes: tail -f logs/alerts.log"
