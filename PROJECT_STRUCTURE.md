# Structure du Projet CRYPTO VIZ

## 📁 Arborescence Complète

```
T-DAT/
│
├── 📄 README.md                    # Documentation principale
├── 📄 QUICKSTART.md                # Guide de démarrage rapide
├── 📄 ARCHITECTURE.md              # Documentation architecture détaillée
├── 📄 PROJECT_STRUCTURE.md         # Ce fichier
├── 📄 .env.example                 # Template configuration
├── 📄 .gitignore                   # Fichiers à ignorer (Git)
├── 📄 docker-compose.yml           # Orchestration Docker
│
├── 📂 crypto_viz_backend/          # Backend Django REST API
│   ├── manage.py                   # Gestionnaire Django
│   ├── requirements.txt            # Dépendances Python
│   ├── Dockerfile                  # Image Docker
│   ├── db.sqlite3                  # Base SQLite (créée après migrate)
│   │
│   ├── crypto_viz/                 # Configuration Django
│   │   ├── __init__.py
│   │   ├── settings.py             # ⚙️ Configuration principale
│   │   ├── urls.py                 # Routes principales
│   │   ├── wsgi.py                 # WSGI app
│   │   └── asgi.py                 # ASGI app
│   │
│   └── api/                        # Application API
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py               # 📊 Modèles Django (métadonnées)
│       ├── admin.py                # Interface admin
│       ├── views.py                # 🔌 Vues REST API
│       ├── serializers.py          # Serializers DRF
│       ├── urls.py                 # Routes API
│       ├── timescale_client.py     # 🔗 Client TimescaleDB
│       └── migrations/             # Migrations Django
│           └── __init__.py
│
├── 📂 spark_jobs/                  # Jobs Spark Streaming
│   ├── requirements.txt            # Dépendances PySpark
│   ├── config.py                   # ⚙️ Configuration Spark
│   ├── schemas.py                  # Schémas Kafka
│   ├── kafka_to_timescale.py       # 🔥 Job d'ingestion
│   └── sentiment_prediction_job.py # 🤖 Job d'analytics
│
├── 📂 database/                    # Scripts SQL
│   └── timescaledb_setup.sql       # 🗄️ Initialisation TimescaleDB
│
├── 📂 scripts/                     # Scripts utilitaires
│   ├── setup_project.sh            # 🛠️ Installation initiale
│   ├── start_all.sh                # ▶️ Démarrer tous les services
│   ├── stop_all.sh                 # ⏹️ Arrêter tous les services
│   ├── test_kafka_connection.py    # 🧪 Test Kafka
│   └── test_timescale_connection.py # 🧪 Test TimescaleDB
│
└── 📂 logs/                        # Logs des services
    └── .gitkeep                    # (Django, Spark logs seront ici)
```

## 📋 Fichiers Clés

### Configuration

| Fichier | Description |
|---------|-------------|
| `.env.example` | Template des variables d'environnement |
| `docker-compose.yml` | Configuration Docker (TimescaleDB, Redis) |
| `crypto_viz/settings.py` | Configuration Django (bases de données, CORS) |
| `spark_jobs/config.py` | Configuration Spark et Kafka |

### Backend Django

| Fichier | Rôle |
|---------|------|
| `api/models.py` | Modèles SQLite (CryptoConfiguration, VisualizationParameter) |
| `api/views.py` | Endpoints REST (sentiment, predictions, ticker, etc.) |
| `api/serializers.py` | Serializers DRF pour JSON |
| `api/timescale_client.py` | Client direct TimescaleDB (sans ORM) |
| `api/urls.py` | Routes API (/api/v1/...) |

### Jobs Spark

| Fichier | Rôle |
|---------|------|
| `kafka_to_timescale.py` | Ingestion des 4 topics Kafka → TimescaleDB |
| `sentiment_prediction_job.py` | Analyse sentiment + prédictions ML |
| `schemas.py` | Schémas Kafka (TICKER, TRADE, ARTICLE, ALERT) |

### Base de Données

| Fichier | Rôle |
|---------|------|
| `timescaledb_setup.sql` | Création des hypertables et index |

### Documentation

| Fichier | Contenu |
|---------|---------|
| `README.md` | Documentation complète |
| `QUICKSTART.md` | Guide rapide (5 minutes) |
| `ARCHITECTURE.md` | Architecture détaillée |
| `PROJECT_STRUCTURE.md` | Structure du projet (ce fichier) |
| `Stratégie d'Intégration...md` | Document de stratégie initial |

## 🔄 Flux de Démarrage

### 1. Installation Initiale

```bash
./scripts/setup_project.sh
```

**Actions effectuées** :
- Création des environnements virtuels Python
- Installation des dépendances (Django, Spark)
- Configuration des permissions
- Création des répertoires nécessaires

### 2. Démarrage des Services

```bash
./scripts/start_all.sh
```

**Services lancés** :
1. TimescaleDB (Docker, port 15432)
2. Redis (Docker, port 6380)
3. Django API (port 8000)
4. Spark Ingestion Job
5. Spark Analytics Job

### 3. Arrêt des Services

```bash
./scripts/stop_all.sh
```

## 📊 Tables TimescaleDB

### Tables de Données Brutes (Kafka → Spark → TimescaleDB)

| Table | Source Kafka | Description |
|-------|--------------|-------------|
| `ticker_data` | rawticker | Prix en temps réel |
| `trade_data` | rawtrade | Transactions |
| `article_data` | rawarticle | Articles avec sentiment |
| `alert_data` | rawalert | Alertes de prix |

### Tables d'Analytics (Spark → TimescaleDB)

| Table | Générée par | Description |
|-------|-------------|-------------|
| `sentiment_data` | Spark Analytics | Sentiment agrégé par crypto |
| `prediction_data` | Spark Analytics | Prédictions de prix ML |

### Vues Matérialisées

| Vue | Agrégation | Rafraîchissement |
|-----|------------|------------------|
| `sentiment_hourly` | 1 heure | Automatique (1h) |
| `ticker_ohlc_hourly` | 1 heure | Automatique (1h) |

## 🌐 Endpoints API

### Configuration (SQLite via ORM Django)

```
GET    /api/v1/config/crypto/              # Liste des cryptos
POST   /api/v1/config/crypto/              # Ajouter une crypto
GET    /api/v1/config/visualization/       # Paramètres de viz
```

### Données Historiques (TimescaleDB via client direct)

```
GET    /api/v1/sentiment/{symbol}/historique/     # Sentiment
GET    /api/v1/prediction/{symbol}/historique/    # Prédictions
GET    /api/v1/ticker/{pair}/historique/          # Prix
GET    /api/v1/trade/{pair}/historique/           # Trades
GET    /api/v1/article/historique/                # Articles
GET    /api/v1/alert/historique/                  # Alertes
GET    /api/v1/health/                            # Health check
```

## 🔧 Variables d'Environnement

### Django (.env)

```bash
SECRET_KEY=...              # Clé secrète Django
DEBUG=True/False            # Mode debug
ALLOWED_HOSTS=*             # Hosts autorisés

KAFKA_SERVERS=...           # Serveur Kafka
TIMESCALE_DB_HOST=...       # Host TimescaleDB
TIMESCALE_DB_NAME=...       # Nom de la base
TIMESCALE_DB_USER=...       # Utilisateur
TIMESCALE_DB_PASSWORD=...   # Mot de passe
```

### Spark (variables système)

```bash
SPARK_MASTER=local[*]       # Mode Spark
CHECKPOINT_LOCATION=...     # Répertoire checkpoints
```

## 📦 Dépendances

### Backend Django (`crypto_viz_backend/requirements.txt`)

```
Django==5.0
djangorestframework==3.14.0
django-cors-headers==4.3.1
psycopg2-binary==2.9.9
kafka-python==2.0.2
channels==4.0.0
channels-redis==4.1.0
gunicorn==21.2.0
```

### Spark Jobs (`spark_jobs/requirements.txt`)

```
pyspark==3.5.0
kafka-python==2.0.2
psycopg2-binary==2.9.9
```

## 🚀 Commandes Utiles

### Django

```bash
# Activer l'environnement
cd crypto_viz_backend
source venv/bin/activate

# Migrations
python manage.py makemigrations
python manage.py migrate

# Créer superuser
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver

# Shell Django
python manage.py shell

# Tests
python manage.py test
```

### Spark

```bash
# Activer l'environnement
cd spark_jobs
source venv/bin/activate

# Lancer l'ingestion
python kafka_to_timescale.py

# Lancer les analytics
python sentiment_prediction_job.py
```

### Docker

```bash
# Démarrer TimescaleDB et Redis
docker compose up -d

# Voir les logs
docker logs -f crypto_viz_timescaledb

# Se connecter à TimescaleDB
docker exec -it crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts

# Arrêter les services
docker compose down

# Supprimer les volumes
docker compose down -v
```

### Tests

```bash
# Test Kafka
python3 scripts/test_kafka_connection.py

# Test TimescaleDB
python3 scripts/test_timescale_connection.py

# Health check API
curl http://localhost:8000/api/v1/health/
```

## 📝 Logs

### Emplacements

```
logs/
├── django.log              # Logs Django API
├── spark_ingestion.log     # Logs Spark Ingestion
└── spark_analytics.log     # Logs Spark Analytics
```

### Suivre les logs en temps réel

```bash
# Django
tail -f logs/django.log

# Spark Ingestion
tail -f logs/spark_ingestion.log

# Spark Analytics
tail -f logs/spark_analytics.log

# TimescaleDB
docker logs -f crypto_viz_timescaledb
```

## 🎯 Prochaines Étapes

- [ ] Implémenter authentification JWT
- [ ] Créer le frontend (React/Vue.js)
- [ ] Ajouter tests unitaires et d'intégration
- [ ] Configurer CI/CD (GitHub Actions)
- [ ] Monitoring avec Prometheus/Grafana
- [ ] Documentation API avec Swagger
- [ ] Optimisations de performance
- [ ] Déploiement en production

## 📚 Documentation Complète

Pour plus de détails, consultez :

- **[README.md](./README.md)** : Documentation principale
- **[QUICKSTART.md](./QUICKSTART.md)** : Guide de démarrage rapide
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** : Architecture technique détaillée
- **[Stratégie d'Intégration](./Stratégie%20d'Intégration%20_%20Backend%20Django%20et%20Traitement%20Spark%20pour%20CRYPTO%20VIZ.md)** : Document de stratégie

---

**Projet** : CRYPTO VIZ  
**Version** : 1.0.0  
**Date** : Novembre 2024
