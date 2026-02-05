# Guide de Déploiement

## Vue d'ensemble

Ce guide explique comment déployer la plateforme CRYPTO VIZ, de l'infrastructure Docker au démarrage des jobs Spark.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DÉPLOIEMENT CRYPTO VIZ                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   PHASE 1: INFRASTRUCTURE (Docker)                                      │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  docker-compose up -d                                           │   │
│   │                                                                   │   │
│   │  Services démarrés:                                             │   │
│   │  ✓ Kafka (9092, 29092)                                          │   │
│   │  ✓ TimescaleDB (15432)                                          │   │
│   │  ✓ Redis (6380)                                                 │   │
│   │  ✓ Django (8000)                                                │   │
│   │  ✓ Prometheus (9090)                                            │   │
│   │  ✓ Grafana (3000)                                               │   │
│   │  ✓ Exporters (9100, 9121, 9187, 9308)                           │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│   PHASE 2: VÉRIFICATION INFRA                                           │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  • Health checks Docker                                         │   │
│   │  • Test connexion Kafka                                         │   │
│   │  • Test connexion TimescaleDB                                   │   │
│   │  • Création topics Kafka                                        │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│   PHASE 3: DATA PRODUCERS                                               │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  • article_scraper.py → Kafka (rawarticle)                      │   │
│   │  • kraken_producer.py → Kafka (rawticker, rawtrade, rawalert)   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│   PHASE 4: SPARK JOBS                                                   │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  • kafka_to_timescale.py → TimescaleDB (4 streams)              │   │
│   │  • sentiment_prediction_job.py → TimescaleDB (2 streams)        │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│   PHASE 5: VÉRIFICATION FINALE                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  • Test API endpoints                                             │   │
│   │  • Vérification données dans TimescaleDB                        │   │
│   │  • Dashboards Grafana                                             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prérequis

### Système

| Ressource | Minimum | Recommandé |
|-----------|---------|------------|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disk | 50 GB SSD | 100 GB SSD |
| OS | Linux (Ubuntu 22.04+) | Linux (Ubuntu 22.04+) |
| Docker | 24.x+ | Dernière version |
| Docker Compose | 2.23+ | Dernière version |

### Dépendances logicielles

```bash
# Java 21 (requis pour Spark)
sudo apt update
sudo apt install openjdk-21-jdk

# Vérification
java -version  # OpenJDK 21

# Python 3.11+
python3 --version  # 3.11.x

# pip
pip3 --version
```

## Phase 1: Infrastructure Docker

### 1.1 Démarrage

```bash
# Cloner le projet (si pas déjà fait)
cd T-DAT

# Copier le fichier d'environnement
cp .env.example .env

# Éditer les variables si nécessaire
nano .env
```

Contenu `.env.example`:
```bash
# PostgreSQL / TimescaleDB
POSTGRES_DB=crypto_viz_ts
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Django
DEBUG=True
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@cryptoviz.com
DJANGO_SUPERUSER_PASSWORD=admin

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin

# Kafka & Spark (local)
KAFKA_SERVERS=localhost:9092
TIMESCALE_HOST=localhost
TIMESCALE_PORT=15432
```

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier le statut
docker-compose ps

# Attendre les health checks (peut prendre 1-2 minutes)
docker-compose logs -f kafka  # Attendre "Kafka broker started"
docker-compose logs -f timescaledb  # Attendre "ready to accept connections"
```

### 1.2 Vérification des services

```bash
# Kafka
docker exec t-dat-kafka-1 /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server localhost:29092

# TimescaleDB
docker exec t-dat-timescaledb-1 pg_isready -U postgres

# Django
curl http://localhost:8000/admin/  # Devrait rediriger vers login

# Prometheus
curl http://localhost:9090/api/v1/status/targets

# Grafana
curl http://localhost:3000/api/health
```

## Phase 2: Configuration Kafka

### 2.1 Création des topics

```bash
# Se connecter au conteneur Kafka
docker exec -it t-dat-kafka-1 bash

cd /opt/kafka/bin

# Créer les topics
./kafka-topics.sh --bootstrap-server localhost:29092 \
  --create --topic rawarticle --partitions 1 --replication-factor 1

./kafka-topics.sh --bootstrap-server localhost:29092 \
  --create --topic rawticker --partitions 1 --replication-factor 1

./kafka-topics.sh --bootstrap-server localhost:29092 \
  --create --topic rawtrade --partitions 1 --replication-factor 1

./kafka-topics.sh --bootstrap-server localhost:29092 \
  --create --topic rawalert --partitions 1 --replication-factor 1

# Vérifier
./kafka-topics.sh --bootstrap-server localhost:29092 --list

# Sortir
exit
```

### 2.2 Test connexion Kafka

```bash
# Via script Python
python3 scripts/test_kafka_connection.py

# Ou manuellement
docker exec t-dat-kafka-1 /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:29092 \
  --topic rawarticle

# Taper un message puis Ctrl+C
# Test{"id": "test", "title": "Test"}
```

## Phase 3: Data Producers

### 3.1 Article Scraper

```bash
# Aller dans le dossier
cd data_producers

# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt

# Lancer le scraper (background)
nohup python article_scraper.py > ../logs/article_scraper.log 2>&1 &

# Vérifier
ps aux | grep article_scraper | grep -v grep
tail -f ../logs/article_scraper.log
```

### 3.2 Kraken Producer

```bash
# Même venv (toujours actif)
source data_producers/venv/bin/activate

# Lancer le producer (background)
nohup python kraken_producer.py > ../logs/kraken_producer.log 2>&1 &

# Vérifier
ps aux | grep kraken_producer | grep -v grep
tail -f ../logs/kraken_producer.log
```

## Phase 4: Spark Jobs

### 4.1 Téléchargement des JARs

```bash
# Rendre le script exécutable
chmod +x scripts/download_spark_jars.sh

# Télécharger les JARs (première fois uniquement)
./scripts/download_spark_jars.sh

# Vérifier
cd spark_jobs
ls -la jars/
# spark-sql-kafka-0-10_2.12-3.5.0.jar
# postgresql-42.7.1.jar
# kafka-clients-3.4.1.jar
```

### 4.2 Job d'ingestion

```bash
# Aller dans spark_jobs
cd spark_jobs

# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt  # pyspark, psycopg2-binary

# Lancer le job (background)
nohup python kafka_to_timescale.py > ../logs/spark_ingestion.log 2>&1 &

# Vérifier
ps aux | grep "kafka_to_timescale" | grep -v grep
tail -f ../logs/spark_ingestion.log
```

Attendre de voir dans les logs:
```
Tous les streams sont actifs!
```

### 4.3 Job d'analyse

```bash
# Toujours dans spark_jobs avec venv activé

# Lancer le job (background)
nohup python sentiment_prediction_job.py > ../logs/spark_analytics.log 2>&1 &

# Vérifier
ps aux | grep "sentiment_prediction" | grep -v grep
tail -f ../logs/spark_analytics.log
```

## Phase 5: Vérification Finale

### 5.1 Vérifier les processus

```bash
# Tous les processus doivent être actifs
ps aux | grep -E "docker|article_scraper|kraken_producer|spark" | grep -v grep

# Doit afficher:
# - dockerd
# - article_scraper.py
# - kraken_producer.py  
# - java (processus Spark)
# - python kafka_to_timescale.py
# - python sentiment_prediction_job.py
```

### 5.2 Vérifier les données

```bash
# Se connecter à TimescaleDB
docker exec -it t-dat-timescaledb-1 psql -U postgres -d crypto_viz_ts

# Vérifier les tables
\dt

# Compter les lignes
SELECT COUNT(*) FROM article_data;
SELECT COUNT(*) FROM ticker_data;
SELECT COUNT(*) FROM sentiment_data;
SELECT COUNT(*) FROM prediction_data;

# Voir les données récentes
SELECT * FROM sentiment_data ORDER BY timestamp DESC LIMIT 5;

# Quitter
\q
```

### 5.3 Tester l'API

```bash
# Test sentiment
curl -s "http://localhost:8000/api/v1/sentiment/bitcoin/historique/?periode=7d" | python3 -m json.tool

# Test prix
curl -s "http://localhost:8000/api/v1/prix/btc/temps_reel/" | python3 -m json.tool

# Test prédictions
curl -s "http://localhost:8000/api/v1/predictions/btc/" | python3 -m json.tool
```

### 5.4 Vérifier Grafana

```bash
# Ouvrir navigateur
open http://localhost:3000  # ou xdg-open

# Login
Username: admin
Password: admin

# Vérifier dashboards
# Home → Dashboards → Manage
```

## Scripts de gestion

### Démarrage complet

```bash
#!/bin/bash
# start_all.sh

echo "=== Démarrage CRYPTO VIZ ==="

# Infrastructure
echo "[1/5] Démarrage Docker..."
docker-compose up -d
sleep 30

# Attendre santé
echo "[2/5] Attente santé services..."
until docker exec t-dat-kafka-1 /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:29092 > /dev/null 2>&1; do
    echo "  Attente Kafka..."
    sleep 5
done
echo "  ✓ Kafka OK"

# Producers
echo "[3/5] Démarrage Data Producers..."
cd data_producers
source venv/bin/activate
nohup python article_scraper.py > ../logs/article_scraper.log 2>&1 &
nohup python kraken_producer.py > ../logs/kraken_producer.log 2>&1 &
cd ..

# Spark
echo "[4/5] Démarrage Spark Jobs..."
cd spark_jobs
source venv/bin/activate
nohup python kafka_to_timescale.py > ../logs/spark_ingestion.log 2>&1 &
nohup python sentiment_prediction_job.py > ../logs/spark_analytics.log 2>&1 &
cd ..

# Vérification
echo "[5/5] Vérification..."
sleep 10

echo "Processus actifs:"
ps aux | grep -E "article_scraper|kraken_producer|spark" | grep -v grep | wc -l
echo ""
echo "=== CRYPTO VIZ démarré ==="
echo "API: http://localhost:8000"
echo "Grafana: http://localhost:3000"
echo ""
```

### Arrêt complet

```bash
#!/bin/bash
# stop_all.sh

echo "=== Arrêt CRYPTO VIZ ==="

# Arrêter Python jobs
echo "[1/3] Arrêt jobs Python..."
pkill -f "article_scraper.py" || true
pkill -f "kraken_producer.py" || true
pkill -f "kafka_to_timescale.py" || true
pkill -f "sentiment_prediction_job.py" || true

# Arrêter Spark (Java)
pkill -f "org.apache.spark.deploy.SparkSubmit" || true

echo "[2/3] Attente arrêt..."
sleep 5

# Arrêter Docker
echo "[3/3] Arrêt Docker..."
docker-compose down

echo "=== CRYPTO VIZ arrêté ==="
```

### Redémarrage Spark (avec nettoyage)

```bash
#!/bin/bash
# restart_spark.sh

echo "Redémarrage Spark avec nettoyage checkpoints..."

# Arrêter
pkill -f "kafka_to_timescale.py" || true
pkill -f "sentiment_prediction_job.py" || true
pkill -f "org.apache.spark.deploy.SparkSubmit" || true

sleep 5

# Nettoyer checkpoints
rm -rf /tmp/spark_checkpoints/*
rm -rf /tmp/spark_checkpoints_sentiment/*
rm -rf /tmp/spark_checkpoints_prediction/*

echo "Checkpoints nettoyés"

# Redémarrer
cd spark_jobs
source venv/bin/activate

nohup python kafka_to_timescale.py > ../logs/spark_ingestion.log 2>&1 &
sleep 2
nohup python sentiment_prediction_job.py > ../logs/spark_analytics.log 2>&1 &

echo "Spark redémarré"
```

## Troubleshooting

### Problème: Kafka ne démarre pas

```bash
# Vérifier logs
docker-compose logs kafka

# Si erreur mémoire, augmenter dans docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 2G  # Au lieu de 1G

# Recréer
docker-compose down
docker-compose up -d
```

### Problème: Spark ne trouve pas les JARs

```bash
# Vérifier présence
ls -la spark_jobs/jars/

# Si vide, télécharger
./scripts/download_spark_jars.sh

# Vérifier permissions
chmod 644 spark_jobs/jars/*.jar
```

### Problème: Connexion TimescaleDB refusée

```bash
# Vérifier conteneur
docker ps | grep timescaledb

# Vérifier logs
docker-compose logs timescaledb

# Tester connexion
docker exec t-dat-timescaledb-1 pg_isready -U postgres

# Si nécessaire, recréer avec données propres
docker-compose down -v  # Supprime les volumes
docker-compose up -d
```

### Problème: Pas de données dans l'API

```bash
# Vérifier que les producers envoient
tail -f logs/article_scraper.log
tail -f logs/kraken_producer.log

# Vérifier Kafka reçoit
docker exec t-dat-kafka-1 /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:29092 \
  --topic rawarticle \
  --from-beginning

# Vérifier Spark traite
tail -f logs/spark_ingestion.log

# Vérifier TimescaleDB reçoit
docker exec t-dat-timescaledb-1 psql -U postgres -d crypto_viz_ts -c \
  "SELECT COUNT(*) FROM article_data;"
```

## Configuration avancée

### Variables d'environnement

```bash
# Créer un fichier .env.local pour overrides
# Ces variables surchargent .env

# Kafka externe
KAFKA_SERVERS=kafka.example.com:9092

# TimescaleDB externe
TIMESCALE_HOST=db.example.com
TIMESCALE_PORT=5432
TIMESCALE_PASSWORD=strong_password

# Spark cluster
SPARK_MASTER=spark://cluster:7077
```

### Scaling

```yaml
# docker-compose.yml - Configuration production
services:
  kafka:
    deploy:
      replicas: 3  # Cluster Kafka
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
  
  spark-worker:
    image: bitnami/spark:latest
    deploy:
      replicas: 2
```

---

**Suite** : [08-monitoring.md](./08-monitoring.md) pour la configuration monitoring.
