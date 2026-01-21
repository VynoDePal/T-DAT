#!/bin/bash

# Script pour redémarrer proprement les jobs Spark

cd "$(dirname "$0")/.."

echo "🔄 Redémarrage des jobs Spark..."

# Arrêter les jobs existants
if [ -f "logs/spark_ingestion.pid" ]; then
    kill $(cat logs/spark_ingestion.pid) 2>/dev/null || true
    rm logs/spark_ingestion.pid
fi

if [ -f "logs/spark_analytics.pid" ]; then
    kill $(cat logs/spark_analytics.pid) 2>/dev/null || true
    rm logs/spark_analytics.pid
fi

# Force kill au cas où
pkill -9 -f "kafka_to_timescale.py" 2>/dev/null || true
pkill -9 -f "sentiment_prediction_job.py" 2>/dev/null || true

sleep 2

# Nettoyer les checkpoints
rm -rf /tmp/spark_checkpoints/* 2>/dev/null || true

cd spark_jobs
source venv/bin/activate

# Démarrer Spark Ingestion
echo "▶️  Démarrage Spark Ingestion..."
nohup python kafka_to_timescale.py > ../logs/spark_ingestion.log 2>&1 &
echo $! > ../logs/spark_ingestion.pid
echo "✅ Spark Ingestion PID: $(cat ../logs/spark_ingestion.pid)"

sleep 2

# Démarrer Spark Analytics
echo "▶️  Démarrage Spark Analytics..."
nohup python sentiment_prediction_job.py > ../logs/spark_analytics.log 2>&1 &
echo $! > ../logs/spark_analytics.pid
echo "✅ Spark Analytics PID: $(cat ../logs/spark_analytics.pid)"

echo "✅ Jobs Spark redémarrés"
