# CRYPTO VIZ - Documentation Technique Complète

> Pipeline de données temps réel pour analyse de sentiment crypto et prédictions de prix

## Vue d'ensemble du projet

**CRYPTO VIZ** est une plateforme d'analyse de données cryptomonnaies en temps réel qui combine :
- **Collecte de données** : Articles crypto depuis RSS + Prix depuis Kraken WebSocket
- **Analyse de sentiment** : TextBlob pour classifier le sentiment (positive/négative/neutral)
- **Prédictions de prix** : Algorithmes de moyenne mobile avec intervalles de confiance
- **API REST** : Backend Django pour consommer les données analytiques
- **Monitoring** : Stack Prometheus + Grafana pour l'observabilité

## Architecture globale

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    SOURCES DE DONNÉES                                   │
├─────────────────────────┬─────────────────────────────────────────────────────────────────┤
│  Flux RSS Crypto        │  WebSocket Kraken API                                          │
│  • CoinDesk             │  • BTC/USD, ETH/USD, SOL/USD...                                │
│  • Cointelegraph        │  • Ticker (prix temps réel)                                    │
│  • Decrypt              │  • Trade (transactions)                                        │
│  • CryptoSlate          │  • Alertes (changements >0.5%)                                 │
│  • Bitcoin Magazine     │                                                                │
└───────────┬─────────────┴──────────────────────────────┬────────────────────────────────┘
            │                                            │
            ▼                                            ▼
┌─────────────────────────┐                  ┌─────────────────────────┐
│   Article Scraper       │                  │   Kraken Producer       │
│   (Python + TextBlob)     │                  │   (Python WebSocket)    │
│                         │                  │                         │
│  • Parse RSS toutes les │                  │  • Connexion persistante│
│    5 minutes            │                  │  • Parse ticker/trade   │
│  • Extrait contenu HTML │                  │  • Détecte anomalies    │
│  • Analyse sentiment    │                  │                         │
└───────────┬─────────────┘                  └───────────┬─────────────┘
            │                                            │
            │    ┌───────────────────────────────────────┘
            │    │
            ▼    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         APACHE KAFKA 4.1.1                            │
│                    (Mode KRaft - Sans ZooKeeper)                      │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┤
│   rawarticle    │   rawticker     │   rawtrade      │    rawalert     │
│   (JSON)        │   (JSON)        │   (JSON)        │    (JSON)       │
│                 │                 │                 │                 │
│ Articles avec   │ Prix temps réel │ Transactions    │ Alertes prix  │
│ sentiment       │ par crypto      │ individuelles   │ significatifs │
└────────┬────────┴────────┬────────┴────────┬────────┴────────┬────────┘
         │                 │                 │                  │
         ▼                 ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              APACHE SPARK STRUCTURED STREAMING                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐ │
│  │  JOB 1: INGESTION        │    │  JOB 2: ANALYTICS            │ │
│  │  kafka_to_timescale.py   │    │  sentiment_prediction_job.py │ │
│  │                          │    │                              │ │
│  │  4 streams parallèles:   │    │  2 streams analytiques:      │ │
│  │  • rawarticle → article_ │    │  • rawarticle → sentiment_   │ │
│  │    data                  │    │    data (agrégé)             │ │
│  │  • rawticker → ticker_   │    │  • rawticker → prediction_   │ │
│  │    data                  │    │    data (prédictions)        │ │
│  │  • rawtrade → trade_     │    │                              │ │
│  │    data                  │    │  Windowing 3 minutes +       │ │
│  │  • rawalert → alert_     │    │  watermarking 2 minutes      │ │
│  │    data                  │    │                              │ │
│  │                          │    │                              │ │
│  │  Transformation:       │    │  Agrégations:                │ │
│  │  JSON parse → struct     │    │  • AVG(sentiment_score)      │ │
│  │  Timestamp conversion    │    │  • STDEV(price)              │ │
│  │  Nested field extract    │    │  • Moving average trends     │ │
│  │                          │    │                              │ │
│  │  Écriture: foreachBatch  │    │  Classification:             │ │
│  │  + JDBC append mode      │    │  >0.6 = positive             │ │
│  │                          │    │  <0.4 = negative             │ │
│  │                          │    │  else = neutral              │ │
│  └──────────┬───────────────┘    └──────────────┬───────────────┘ │
│             │                                    │                 │
└─────────────┼────────────────────────────────────┼─────────────────┘
              │                                    │
              ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TIMESCALEDB (PostgreSQL 18)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   TABLES HYPERTABLES (Séries temporelles partitionnées)             │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│   │ ticker_data     │  │ trade_data      │  │ article_data        │ │
│   ├─────────────────┤  ├─────────────────┤  ├─────────────────────┤ │
│   │ timestamp       │  │ timestamp       │  │ timestamp           │ │
│   │ pair            │  │ pair            │  │ article_id            │ │
│   │ last            │  │ price           │  │ title                 │ │
│   │ bid             │  │ volume          │  │ url                   │ │
│   │ ask             │  │ side            │  │ website               │ │
│   │ volume_24h      │  │                 │  │ summary               │ │
│   │                 │  │                 │  │ cryptocurrencies_     │ │
│   │                 │  │                 │  │   mentioned           │ │
│   │                 │  │                 │  │ sentiment_score       │ │
│   │                 │  │                 │  │ sentiment_label       │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│   │ alert_data      │  │ sentiment_data  │  │ prediction_data     │ │
│   ├─────────────────┤  ├─────────────────┤  ├─────────────────────┤ │
│   │ timestamp       │  │ timestamp       │  │ timestamp           │ │
│   │ pair            │  │ crypto_symbol   │  │ crypto_symbol         │ │
│   │ last_price      │  │ sentiment_score │  │ predicted_price       │ │
│   │ change_percent  │  │ sentiment_label │  │ actual_price          │ │
│   │ threshold       │  │ source          │  │ model_name            │ │
│   │ alert_type      │  │ confidence      │  │ confidence_interval_  │ │
│   │                 │  │                 │  │   low/high            │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DJANGO REST API (Python)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ENDPOINTS PRINCIPAUX:                                             │
│                                                                     │
│   GET /api/v1/sentiment/{crypto}/historique/?periode=7d             │
│   → Historique sentiment agrégé par time_bucket                   │
│                                                                     │
│   GET /api/v1/prix/{crypto}/historique/                             │
│   → Historique des prix                                           │
│                                                                     │
│   GET /api/v1/prix/{crypto}/temps_reel/                             │
│   → Dernier prix connu                                             │
│                                                                     │
│   GET /api/v1/predictions/{crypto}/                                 │
│   → Prédictions avec métriques de confiance                       │
│                                                                     │
│   GET /api/v1/articles/{crypto}/                                    │
│   → Articles liés à une crypto                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     MONITORING & OBSERVABILITÉ                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   PROMETHEUS (9090)  →  Métriques système + application             │
│   GRAFANA (3000)     →  Dashboards visualisation                    │
│                                                                     │
│   EXPORTERS:                                                        │
│   • node-exporter (9100)    → CPU, RAM, Disk, Network               │
│   • kafka-exporter (9308)   → Topics, Consumer Lag, Throughput      │
│   • postgres-exporter (9187)→ Queries, Connections, Locks           │
│   • redis-exporter (9121)   → Memory, Operations, Hits/Misses       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Technologies utilisées

| Couche | Technologie | Version | Rôle |
|--------|-------------|---------|------|
| **Ingestion** | Python | 3.11+ | Scrapers et producers |
| | TextBlob | 0.19.0 | Analyse de sentiment |
| | feedparser | 6.0.x | Parsing RSS |
| | websocket-client | 1.6.x | Connexion WebSocket |
| | confluent-kafka | 2.3.x | Client Kafka |
| **Message Broker** | Apache Kafka | 4.1.1 | Streaming events |
| **Traitement** | Apache Spark | 3.5.0 | Structured Streaming |
| | PySpark | 3.5.0 | API Python Spark |
| **Stockage** | TimescaleDB | PG18 | Séries temporelles |
| | PostgreSQL | 16.x | Moteur relationnel |
| **Backend** | Django | 4.2+ | Framework web |
| | DRF | 3.14+ | API REST |
| | gunicorn | 21.x | WSGI server |
| **Monitoring** | Prometheus | 2.55.0 | Collecte métriques |
| | Grafana | 11.3.0 | Visualisation |
| **Infrastructure** | Docker | 24.x | Conteneurisation |
| | Docker Compose | 2.23+ | Orchestration |

## Structure du projet

```
T-DAT/
├── docker-compose.yml              # Orchestration des services
├── README.md                       # Vue d'ensemble
├── .env.example                    # Variables d'environnement
│
├── data_producers/                 # COUCHE D'INGESTION
│   ├── article_scraper.py          # Scraper RSS + sentiment
│   ├── kraken_producer.py          # Producer WebSocket Kraken
│   └── requirements.txt            # Dépendances Python
│
├── spark_jobs/                     # COUCHE DE TRAITEMENT
│   ├── kafka_to_timescale.py       # Job d'ingestion (4 streams)
│   ├── sentiment_prediction_job.py # Job d'analyse (2 streams)
│   ├── config.py                   # Configuration Spark/Kafka/DB
│   ├── schemas.py                  # Schémas de données
│   └── jars/                       # JARs externes
│       ├── spark-sql-kafka-*.jar
│       ├── postgresql-*.jar
│       └── kafka-clients-*.jar
│
├── crypto_viz_backend/             # COUCHE API
│   ├── api/                        # Application Django
│   │   ├── views.py                # Endpoints REST
│   │   ├── models.py               # Modèles de données
│   │   ├── serializers.py          # Sérializers DRF
│   │   ├── timescale_client.py     # Client DB raw SQL
│   │   └── urls.py                 # Routing API
│   ├── crypto_viz/                 # Configuration projet
│   │   ├── settings.py             # Paramètres Django
│   │   ├── urls.py                 # URLs principales
│   │   └── wsgi.py                 # Entry point WSGI
│   ├── manage.py                   # CLI Django
│   └── requirements.txt            # Dépendances Python
│
├── database/                       # COUCHE STOCKAGE
│   └── timescaledb_setup.sql       # Schéma initial + hypertables
│
├── monitoring/                     # COUCHE OBSERVABILITÉ
│   ├── prometheus/
│   │   └── prometheus.yml          # Configuration scraping
│   ├── grafana/
│   │   ├── provisioning/           # Datasources & dashboards
│   │   └── dashboards/             # Dashboards JSON
│   └── health_check.py             # Script de santé
│
├── scripts/                        # UTILITAIRES
│   ├── download_spark_jars.sh      # Téléchargement JARs
│   ├── test_kafka_connection.py    # Test connexion Kafka
│   └── test_timescale_connection.py # Test connexion DB
│
├── logs/                           # LOGS D'EXÉCUTION
│   ├── article_scraper.log
│   ├── kraken_producer.log
│   ├── spark_ingestion.log
│   └── spark_analytics.log
│
└── doc/                            # DOCUMENTATION COMPLÈTE
    ├── README.md                   # Ce fichier - Vue d'ensemble
    ├── 01-architecture.md          # Architecture détaillée
    ├── 02-data-producers.md        # Data producers en détail
    ├── 03-kafka.md                 # Configuration Kafka
    ├── 04-spark-streaming.md       # Jobs Spark détaillés
    ├── 05-timescaledb.md           # Schéma et requêtes
    ├── 06-backend-api.md           # API Django
    ├── 07-deployment.md            # Guide de déploiement
    └── 08-monitoring.md            # Monitoring et alerting
```

## Workflow de données (End-to-End)

### Exemple 1 : Article RSS → Sentiment Agrégé

```
ÉTAPE 1 : SOURCE (CoinDesk RSS)
↓
Article: "Bitcoin hits new all-time high amid institutional adoption"
Published: 2024-01-15 14:30:00 UTC

ÉTAPE 2 : SCRAPER (article_scraper.py)
↓
• Parse flux RSS (feedparser)
• Extrait titre, résumé, URL
• Analyse sentiment avec TextBlob:
  - Text: "Bitcoin hits new all-time high amid institutional adoption"
  - Polarity: +0.6 (positif)
  - Score converti: (0.6 + 1) / 2 = 0.8
  - Label: "positive" (> 0.6)
• Extraction cryptos: ["bitcoin", "btc"]
• Payload JSON généré:
  {
    "id": "https://coindesk.com/article-123",
    "title": "Bitcoin hits new all-time high...",
    "sentiment": {"score": 0.8, "label": "positive"},
    "cryptocurrencies_mentioned": ["bitcoin", "btc"]
  }

ÉTAPE 3 : KAFKA (rawarticle topic)
↓
• Message publié avec clé: "CoinDesk"
• Sérialisation: JSON UTF-8
• Partition: hash(clé) % num_partitions

ÉTAPE 4 : SPARK JOB 1 - INGESTION (kafka_to_timescale.py)
↓
• Stream lit topic rawarticle
• Parsing JSON avec schéma ARTICLE_SCHEMA
• Transformation:
  - Nested extraction: sentiment.score, sentiment.label
  - Timestamp conversion: unix → TimestampType
• Écriture JDBC:
  INSERT INTO article_data (timestamp, article_id, title, ...)
  VALUES (NOW(), 'https://coindesk.com/article-123', ...)

ÉTAPE 5 : SPARK JOB 2 - ANALYTICS (sentiment_prediction_job.py)
↓
• Stream lit topic rawarticle
• Explosion cryptocurrencies_mentioned:
  - 1 article avec ["bitcoin", "btc"] → 2 lignes
• Windowing 3 minutes + Watermark 2 minutes:
  - Regroupement par crypto_symbol et fenêtre temporelle
• Agrégation:
  SELECT 
    crypto_symbol,
    AVG(sentiment_score) as avg_sentiment,
    AVG(confidence) as avg_confidence
  FROM ...
  GROUP BY window(timestamp, '3 minutes'), crypto_symbol
• Classification label:
  - avg_sentiment > 0.6 → "positive"
  - avg_sentiment < 0.4 → "negative"
  - else → "neutral"
• Écriture JDBC:
  INSERT INTO sentiment_data 
  VALUES (window_end, 'bitcoin', 0.75, 'positive', 'aggregated_articles', 0.8)

ÉTAPE 6 : API DJANGO (/api/v1/sentiment/bitcoin/historique/)
↓
• Requête SQL optimisée TimescaleDB:
  SELECT 
    time_bucket('1 hour', timestamp) as bucket,
    AVG(sentiment_score) as avg_score,
    COUNT(*) as article_count
  FROM sentiment_data
  WHERE crypto_symbol = 'bitcoin'
    AND timestamp > NOW() - INTERVAL '7 days'
  GROUP BY bucket
  ORDER BY bucket DESC
• Réponse JSON:
  {
    "crypto_symbol": "BITCOIN",
    "count": 168,
    "data": [
      {"timestamp": "2024-01-15T14:00:00Z", "sentiment_score": 0.75, ...},
      ...
    ]
  }

ÉTAPE 7 : CLIENT (Frontend/Dashboard)
↓
• Affichage du graphique de sentiment
• Visualisation des tendances sur 7 jours
```

### Exemple 2 : Prix Kraken → Prédiction

```
ÉTAPE 1 : SOURCE (Kraken WebSocket)
↓
Message ticker reçu:
[1234567890, {"c": ["99950.5", "1.5"], "v": ["15000.5", "15000.5"]}, "ticker", "XBT/USD"]

ÉTAPE 2 : PRODUCER (kraken_producer.py)
↓
• Parsing message WebSocket
• Extraction:
  - pair: "XBT/USD"
  - last: 99950.50
  - volume_24h: 15000.5
  - timestamp: 1705312345.678
• Calcul changement prix:
  - previous_price: 97500.00
  - pct_change: ((99950.50 - 97500) / 97500) * 100 = 2.51%
• Détection alerte: |2.51%| > 0.5% → Envoi alerte
• Payload JSON:
  {
    "pair": "XBT/USD",
    "last": 99950.50,
    "volume_24h": 15000.5,
    "timestamp": 1705312345.678,
    "pct_change": 2.51
  }

ÉTAPE 3 : KAFKA (rawticker topic)
↓
Message publié avec clé: "XBT/USD"

ÉTAPE 4 : SPARK JOB 1 - INGESTION
↓
• Parsing avec TICKER_SCHEMA
• Conversion timestamp
• Écriture: INSERT INTO ticker_data VALUES (...)

ÉTAPE 5 : SPARK JOB 2 - ANALYTICS
↓
• Extraction crypto_symbol: split("XBT/USD", '/')[0] → "XBT"
• Windowing: 3 minutes window, 30 secondes slide
• Agrégation par fenêtre:
  SELECT
    crypto_symbol,
    AVG(last) as avg_price,
    STDDEV(last) as price_volatility,
    MIN(last) as min_price,
    MAX(last) as max_price
  FROM ticker_data
  GROUP BY window(timestamp, '3 minutes', '30 seconds'), crypto_symbol
• Prédiction:
  - predicted_price = avg_price
  - confidence_interval_low = avg_price - price_volatility
  - confidence_interval_high = avg_price + price_volatility
• Écriture: INSERT INTO prediction_data VALUES (...)

ÉTAPE 6 : API DJANGO (/api/v1/predictions/btc/)
↓
• Requête dernière prédiction:
  SELECT * FROM prediction_data 
  WHERE crypto_symbol = 'BTC' 
  ORDER BY timestamp DESC LIMIT 1
• Réponse JSON avec métriques de confiance
```

## Table des matières de la documentation

| Document | Contenu | Public cible |
|----------|---------|--------------|
| `01-architecture.md` | Architecture technique détaillée, flux de données, composants | Architectes, Tech Leads |
| `02-data-producers.md` | Article Scraper et Kraken Producer, parsing, formats | Développeurs backend |
| `03-kafka.md` | Configuration Kafka, topics, partitions, sérialisation | DevOps, Backend |
| `04-spark-streaming.md` | Jobs Spark, transformations, windowing, checkpointing | Data Engineers |
| `05-timescaledb.md` | Schéma SQL, hypertables, indexation, requêtes optimisées | DBAs, Backend |
| `06-backend-api.md` | Endpoints Django, sérializers, timescale_client | Développeurs fullstack |
| `07-deployment.md` | Guide déploiement, configuration, troubleshooting | DevOps, SRE |
| `08-monitoring.md` | Prometheus, Grafana, alertes, métriques | SRE, Ops |

## Démarrage rapide

```bash
# 1. Cloner et naviguer
git clone <repo>
cd T-DAT

# 2. Infrastructure (Docker)
docker-compose up -d

# 3. Vérifier santé
docker-compose ps
./scripts/test_kafka_connection.py
./scripts/test_timescale_connection.py

# 4. Data Producers
cd data_producers
pip install -r requirements.txt
python article_scraper.py > ../logs/article_scraper.log 2>&1 &
python kraken_producer.py > ../logs/kraken_producer.log 2>&1 &

# 5. Spark Jobs
cd ../spark_jobs
./scripts/download_spark_jars.sh  # Première fois uniquement
python kafka_to_timescale.py > ../logs/spark_ingestion.log 2>&1 &
python sentiment_prediction_job.py > ../logs/spark_analytics.log 2>&1 &

# 6. Test API
curl http://localhost:8000/api/v1/sentiment/bitcoin/historique/?periode=7d
curl http://localhost:8000/api/v1/prix/btc/temps_reel/

# 7. Monitoring
curl http://localhost:9090/metrics      # Prometheus
open http://localhost:3000              # Grafana (admin/admin)
```

## Contribution et maintenance

- **Issues** : Signaler bugs via le système de suivi
- **PR** : Soumettre modifications avec tests
- **Logs** : Vérifier `logs/` en cas d'anomalie
- **Monitoring** : Dashboards Grafana pour health check

## Licence

Projet éducatif - Tous droits réservés

---

**Prochaine lecture recommandée** : [01-architecture.md](./01-architecture.md) pour comprendre l'architecture technique en profondeur.
