# CRYPTO VIZ - Plateforme de Visualisation Crypto Temps Réel

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://djangoproject.com)
[![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange.svg)](https://spark.apache.org)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-PG18-4E9A06.svg)](https://www.timescale.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Système complet de visualisation et d'analyse de crypto-monnaies en temps réel intégrant Django REST Framework, Apache Spark Streaming, TimescaleDB et un monitoring Prometheus/Grafana.

---

## Table des Matières

- [Vue d'Ensemble](#-vue-densemble)
- [Architecture](#-architecture)
- [Stack Technique](#-stack-technique)
- [Installation](#-installation)
- [Documentation API](#-documentation-api-swagger)
- [Endpoints API](#-endpoints-api)
- [Démarrage Rapide](#-démarrage-rapide)
- [Structure du Projet](#-structure-du-projet)
- [Configuration](#-configuration)
- [Monitoring](#-monitoring)
- [Développement Frontend](#-guide-dintégration-frontend)
- [Contribution](#-contribution)

---

## Vue d'Ensemble

**CRYPTO VIZ** est une plateforme complète offrant :

| Fonctionnalité | Description |
|----------------|-------------|
| **Prix Temps Réel** | Données de marché Kraken en streaming |
| **Analyse de Sentiment** | NLP sur articles crypto |
| **Prédictions ML** | Modèles de prévision de prix |
| **Alertes Prix** | Notifications de variations significatives |
| **Agrégation d'Articles** | Collecte et analyse automatique |
| **Historique Complet** | 90 jours de données avec TimescaleDB |
| **WebSocket Live** | Streaming temps réel via Django Channels |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SOURCES DE DONNÉES                              │
│                     Kraken WebSocket API                                │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
        ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
        │ rawticker │    │ rawtrade  │    │rawarticle │
        │   Topic   │    │   Topic   │    │   Topic   │
        └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
              │                │                 │
              └────────────────┼─────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                                 │
        ┌─────▼──────────┐            ┌────────▼────────┐
        │  SPARK JOB 1   │            │   SPARK JOB 2   │
        │  Ingestion     │            │   Analytics     │
        │  ───────────── │            │  ─────────────  │
        │  • Ticker      │            │  • Sentiment    │
        │  • Trade       │            │  • Predictions  │
        │  • Article     │            │                 │
        │  • Alert       │            │                 │
        └─────┬──────────┘            └────────┬────────┘
              │                                │
              └────────────────┬───────────────┘
                               │
                        ┌──────▼──────┐
                        │ TimescaleDB │
                        │ (PostgreSQL)│
                        │  Hypertables│
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │   Django    │
                        │  REST API   │
                        │ ─────────── │
                        │ Swagger UI  │
                        └──────┬──────┘
                               │
                    ┌──────────┼──────────┐
                    │                     │
             ┌──────▼──────┐      ┌──────▼──────┐
             │   HTTP API  │      │  WebSocket  │
             │   (REST)    │      │  (Channels) │
             └──────┬──────┘      └──────┬──────┘
                    │                     │
                    └──────────┬──────────┘
                               │
                        ┌──────▼──────┐
                        │  Frontend   │
                        │ (React/Vue) │
                        └─────────────┘
```

---

## Stack Technique

### Backend & API
| Technologie | Version | Rôle |
|-------------|---------|------|
| Python | 3.11+ | Langage principal |
| Django | 5.0 | Framework web |
| Django REST Framework | 3.14 | API REST |
| drf-spectacular | 0.27 | Documentation Swagger/OpenAPI |
| Gunicorn | 21.2 | Serveur WSGI |

### Data Pipeline
| Technologie | Version | Rôle |
|-------------|---------|------|
| Apache Kafka | 7.7 | Message broker |
| Apache Spark | 3.5 | Traitement streaming |
| PySpark | 3.5 | API Python pour Spark |

### Bases de Données
| Technologie | Version | Rôle |
|-------------|---------|------|
| TimescaleDB | PG18 | Séries temporelles |
| SQLite | - | Métadonnées Django |
| Redis | 8 | Cache & sessions |

### Monitoring
| Technologie | Version | Rôle |
|-------------|---------|------|
| Prometheus | Latest | Métriques |
| Grafana | Latest | Dashboards |
| Node Exporter | Latest | Métriques système |

---

## Structure du Projet

```
T-DAT/
│
├── crypto_viz_backend/             # Backend Django REST API
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── crypto_viz/                 # Configuration Django
│   │   ├── settings.py             # Config (DB, Swagger, Cache)
│   │   ├── urls.py                 # Routes principales + Swagger
│   │   └── wsgi.py
│   └──  api/                       # Application API
│       ├── models.py               # Modèles SQLite
│       ├── views.py                # Endpoints REST documentés
│       ├── serializers.py          # Serializers avec exemples
│       ├── timescale_client.py     # Client TimescaleDB
│       └── urls.py                 # Routes API v1
│
├── spark_jobs/                     # Jobs Spark Streaming
│   ├── kafka_to_timescale.py       # Ingestion temps réel
│   ├── sentiment_prediction_job.py # ML & Analytics
│   ├── config.py                   # Configuration Spark
│   ├── schemas.py                  # Schémas Kafka
│   └── jars/                       # JARs Spark (Kafka, PostgreSQL)
│
├── data_producers/                 # Producteurs de données
│   ├── kraken_producer.py          # WebSocket Kraken → Kafka
│   ├── article_scraper.py          # Scraping articles crypto
│   └── start_producers.sh
│
├── database/                       # Scripts SQL
│   └── timescaledb_setup.sql       # Schéma TimescaleDB
│
├── monitoring/                     # Configuration monitoring
│   ├── prometheus/                 # Config Prometheus
│   ├── grafana/                    # Dashboards Grafana
│   └── health_check.py
│
├── scripts/                        # Scripts utilitaires
│   ├── start_all.sh                # Démarrer tous les services
│   ├── stop_all.sh                 # Arrêter les services
│   └── diagnostic.sh               # Diagnostic système
│
├── docker-compose.yml              # Orchestration Docker
├── .env.example                    # Variables d'environnement
└── README.md                       # Cette documentation
```

---

## Documentation API (Swagger)

L'API est entièrement documentée avec **Swagger/OpenAPI 3.0** grâce à drf-spectacular.

### Accès à la Documentation

| Interface | URL | Description |
|-----------|-----|-------------|
| **Swagger UI** | http://localhost:8000/api/docs/ | Interface interactive |
| **ReDoc** | http://localhost:8000/api/redoc/ | Documentation lisible |
| **Schema JSON** | http://localhost:8000/api/schema/ | Schéma OpenAPI brut |

### Aperçu Swagger UI

La documentation Swagger offre :
- ✅ **Test interactif** des endpoints directement depuis le navigateur
- ✅ **Exemples de requêtes/réponses** pour chaque endpoint
- ✅ **Descriptions détaillées** des paramètres et schémas
- ✅ **Code snippets** pour l'intégration frontend

### Télécharger le Schema OpenAPI

```bash
# Télécharger le schéma pour génération de client
curl http://localhost:8000/api/schema/ -o openapi-schema.yaml

# Générer un client TypeScript (exemple avec openapi-generator)
npx @openapitools/openapi-generator-cli generate \
  -i openapi-schema.yaml \
  -g typescript-fetch \
  -o ./src/api-client
```

---

## Installation

### 1. Prérequis

| Outil | Version | Vérification |
|-------|---------|--------------|
| Python | 3.11+ | `python --version` |
| Docker | 20.0+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| Java | 11+ | `java -version` |

### 2. Cloner le projet

```bash
git clone https://github.com/your-repo/T-DAT.git
cd T-DAT
```

### 3. Configuration

```bash
# Copier le template de configuration
cp .env.example .env

# Éditer les variables (optionnel pour dev local)
nano .env
```

### 4. Démarrer l'infrastructure Docker

```bash
# Démarrer tous les services (recommandé)
docker compose up -d

# Ou démarrer uniquement les services essentiels
docker compose up -d timescaledb redis kafka
```

### 5. Configuration Backend Django

```bash
cd crypto_viz_backend

# Créer et activer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Installer les dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Créer un superuser (optionnel)
python manage.py createsuperuser

# Démarrer le serveur de développement
python manage.py runserver 0.0.0.0:8000
```

### 6. Lancer les Jobs Spark

```bash
# Terminal 1 - Job d'ingestion
cd spark_jobs
source venv/bin/activate
python kafka_to_timescale.py

# Terminal 2 - Job d'analytics
cd spark_jobs
source venv/bin/activate
python sentiment_prediction_job.py
```

### 7. Démarrer les producteurs de données

```bash
cd data_producers
./start_producers.sh
```

### 8. Vérifier l'installation

```bash
# Health check API
curl http://localhost:8000/api/v1/health/

# Accéder à Swagger
open http://localhost:8000/api/docs/
```

---

## Endpoints API

### Vue d'ensemble

| Catégorie | Endpoint | Méthode | Description |
|-----------|----------|---------|-------------|
| **Health** | `/api/v1/health/` | GET | Vérification santé |
| **Sentiment** | `/api/v1/sentiment/{symbol}/historique/` | GET | Historique sentiment |
| **Predictions** | `/api/v1/prediction/{symbol}/historique/` | GET | Prédictions prix |
| **Tickers** | `/api/v1/ticker/{pair}/historique/` | GET | Historique prix |
| **Trades** | `/api/v1/trade/{pair}/historique/` | GET | Historique transactions |
| **Articles** | `/api/v1/article/historique/` | GET | Articles crypto |
| **Alerts** | `/api/v1/alert/historique/` | GET | Alertes prix |
| **WebSocket Live** | `/ws/live/{pair}/` | WS | Flux temps réel |
| **WebSocket Global** | `/ws/global/` | WS | Alertes & actualités |
| **Config** | `/api/v1/config/crypto/` | GET/POST | Config cryptos |
| **Config** | `/api/v1/config/visualization/` | GET/POST | Config visualisation |

### Paramètres communs

| Paramètre | Type | Description | Valeurs |
|-----------|------|-------------|---------|
| `periode` | string | Période de filtrage | `1h`, `24h`, `7d`, `30d` |
| `date_debut` | datetime | Date de début | ISO 8601 |
| `date_fin` | datetime | Date de fin | ISO 8601 |

### Exemples de requêtes

```bash
# Sentiment Bitcoin sur 24h
curl "http://localhost:8000/api/v1/sentiment/BTC/historique/?periode=24h"

# Prédictions Ethereum sur 7 jours
curl "http://localhost:8000/api/v1/prediction/ETH/historique/?periode=7d"

# Prix XBT/USD sur la dernière heure
curl "http://localhost:8000/api/v1/ticker/XBT%2FUSD/historique/?periode=1h"

# Trades avec dates personnalisées
curl "http://localhost:8000/api/v1/trade/ETH%2FUSD/historique/?date_debut=2024-01-01T00:00:00Z&date_fin=2024-01-15T23:59:59Z"

# Articles mentionnant Bitcoin
curl "http://localhost:8000/api/v1/article/historique/?crypto_symbol=BTC&periode=24h"

# Alertes de variation de prix
curl "http://localhost:8000/api/v1/alert/historique/?pair=XBT/USD&periode=7d"
```

### Exemple de réponse

```json
{
  "crypto_symbol": "BTC",
  "count": 2,
  "data": [
    {
      "timestamp": "2024-01-15T14:30:00.000000Z",
      "crypto_symbol": "BTC",
      "sentiment_score": 0.85,
      "sentiment_label": "positive",
      "source": "aggregated_articles",
      "confidence": 0.92
    },
    {
      "timestamp": "2024-01-15T14:25:00.000000Z",
      "crypto_symbol": "BTC",
      "sentiment_score": 0.72,
      "sentiment_label": "positive",
      "source": "aggregated_articles",
      "confidence": 0.88
    }
  ]
}
```

---


## Configuration

### Variables d'environnement (.env)

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=*

# TimescaleDB
TIMESCALE_DB_HOST=localhost
TIMESCALE_DB_PORT=15432
TIMESCALE_DB_NAME=crypto_viz_ts
TIMESCALE_DB_USER=postgres
TIMESCALE_DB_PASSWORD=password

# Kafka
KAFKA_SERVERS=localhost:9092

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## Monitoring

### Accès aux interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Django Admin** | http://localhost:8000/admin/ | superuser |
| **Spark UI** | http://localhost:4040 | - |

### Métriques disponibles

- **Kafka** : Messages/sec, lag consommateurs, partitions
- **TimescaleDB** : Connexions, requêtes/sec, taille des chunks
- **Django** : Requêtes HTTP, latence, erreurs
- **Système** : CPU, RAM, disque, réseau

---

## Sécurité

### Recommandations pour la production

| Aspect | Action |
|--------|--------|
| **SECRET_KEY** | Générer une clé unique et sécurisée |
| **DEBUG** | Mettre à `False` |
| **CORS** | Restreindre `CORS_ALLOWED_ORIGINS` |
| **HTTPS** | Configurer SSL/TLS |
| **Auth** | Implémenter JWT (prévu) |
| **Rate Limiting** | Déjà configuré (100/h anon, 1000/h auth) |

---

## Tests

```bash
# Tests Django
cd crypto_viz_backend
python manage.py test

# Vérification des endpoints
curl http://localhost:8000/api/v1/health/
```

---

## Déploiement Docker

```bash
# Démarrer tous les services
docker compose up -d

# Voir les logs
docker compose logs -f

# Arrêter les services
docker compose down

# Reconstruire après modifications
docker compose up -d --build
```

---

## Prérequis Spark

Les jobs Spark nécessitent les JARs suivants dans `spark_jobs/jars/`:

| JAR | Description |
|-----|-------------|
| `spark-sql-kafka-0-10_2.12-3.5.0.jar` | Connecteur Kafka pour Spark |
| `postgresql-42.7.1.jar` | Driver JDBC PostgreSQL |
| `kafka-clients-3.5.1.jar` | Client Kafka |

### Télécharger les JARs

```bash
./scripts/download_spark_jars.sh
```

Ou manuellement:
```bash
cd spark_jobs/jars
wget https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar
wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar
```

---

## Dépannage

### Problèmes courants

| Problème | Cause | Solution |
|----------|-------|----------|
| `Connection refused` Kafka | Kafka non démarré | Attendre 40s après `docker compose up` |
| `NoClassDefFoundError` | JARs Spark manquants | Exécuter `download_spark_jars.sh` |
| `psycopg2.OperationalError` | TimescaleDB non prête | Vérifier `docker ps` et ports |
| Port 9092 occupé | Service Kafka local | Arrêter le service: `sudo systemctl stop kafka` |
| Permission denied | Problème Docker | Ajouter user au groupe docker: `sudo usermod -aG docker $USER` |

### Logs utiles

```bash
# Logs Spark
tail -f logs/spark_ingestion.log
tail -f logs/spark_analytics.log

# Logs Kafka
docker logs t-dat-kafka-1 -f

# Logs Django
docker logs t-dat-django-1 -f
```

### Réinitialisation complète

```bash
# Arrêter tout
./scripts/stop_all.sh

# Supprimer les données
docker compose down -v
rm -rf logs/*.log logs/*.pid

# Relancer
./scripts/start_all.sh
```
