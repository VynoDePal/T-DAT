# Architecture Technique CRYPTO VIZ

## Vue d'ensemble de l'architecture

L'architecture CRYPTO VIZ suit un pattern **Lambda simplifié** avec les couches :

1. **Ingestion** (Batch + Streaming)
2. **Message Broker** (Kafka)
3. **Traitement** (Spark Streaming)
4. **Stockage** (TimescaleDB)
5. **API** (Django)
6. **Monitoring** (Prometheus + Grafana)

## Diagramme architectural détaillé

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                   │
├──────────────────────────────┬──────────────────────────────────────────────┤
│       RSS Feeds              │         Kraken WebSocket                     │
│  ┌─────────┐ ┌─────────┐     │     ┌─────────────────────────────┐          │
│  │CoinDesk │ │Cointele │     │     │  wss://ws.kraken.com        │          │
│  │Decrypt  │ │graph    │─────┼────▶│                             │          │
│  │CryptoS..│ │...      │     │     │  • Ticker channel           │          │
│  └────┬────┘ └────┬────┘     │     │  • Trade channel            │          │
│       └───────────┘          │     └──────────────┬──────────────┘          │
└──────────────────────────────┴────────────────────┼─────────────────────────┘
                                                    │
┌───────────────────────────────────────────────────┴─────────────────────────┐
│                         DATA PRODUCERS LAYER                                │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────────┐ │
│  │   article_scraper.py    │    │     kraken_producer.py                  │ │
│  │  ┌───────────────────┐  │    │  ┌─────────────────────────────────┐    │ │
│  │  │ Feed Parsing      │  │    │  │ WebSocket Connection            │    │ │
│  │  │ (feedparser)      │  │    │  │ (websocket-client)              │    │ │
│  │  └─────────┬─────────┘  │    │  └────────────┬────────────────────┘    │ │
│  │            ▼            │    │               ▼                         │ │
│  │  ┌───────────────────┐  │    │  ┌─────────────────────────────────┐    │ │
│  │  │ Content Extract   │  │    │  │ Message Parser                  │    │ │
│  │  │ (BeautifulSoup)   │  │    │  │ • ticker: price, volume         │    │ │
│  │  └─────────┬─────────┘  │    │  │ • trade: price, vol, side       │    │ │
│  │            ▼            │    │  └────────────┬────────────────────┘    │ │
│  │  ┌───────────────────┐  │    │               ▼                         │ │
│  │  │ Sentiment Analysis│  │    │  ┌─────────────────────────────────┐    │ │
│  │  │ (TextBlob)        │  │    │  │ Alert Detection                 │    │ │
│  │  │ polarity→score    │  │    │  │ price_change > 0.5%             │    │ │
│  │  └─────────┬─────────┘  │    │  └────────────┬────────────────────┘    │ │
│  │            ▼            │    │               │                         │ │
│  │  ┌───────────────────┐  │    │               │                         │ │
│  │  │ JSON Payload      │  │    │               │                         │ │
│  │  └─────────┬─────────┘  │    │               │                         │ │
│  └────────────┼────────────┘    └───────────────|─────────────────────────┘ │
└───────────────┼─────────────────────────────────|───────────────────────────┘
                │                                 |
                └─────────────────┬───────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APACHE KAFKA LAYER                                │
│                     (Apache Kafka 4.1.1 - KRaft Mode)                       │
├────────────────┬────────────────┬────────────────┬──────────────────────────┤
│  rawarticle    │  rawticker     │   rawtrade     │    rawalert              │
│  ───────────── │  ───────────── │  ───────────── │    ────────────          │
│  Partition: 0  │  Partition: 0  │  Partition: 0  │    Partition: 0          │
│  Replicas: 1   │  Replicas: 1   │  Replicas: 1   │    Replicas: 1           │
│                │                │                │                          │
│  Key: source   │  Key: pair     │  Key: pair     │    Key: pair             │
│  Value: JSON   │  Value: JSON   │  Value: JSON   │    Value: JSON           │
│  Retention: 7d │  Retention: 7d │  Retention: 7d │    Retention: 1d         │
└────────┬───────┴────────┬───────┴────────┬───────┴────────┬─────────────────┘
         │                │                │                │
         ▼                ▼                ▼                ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                     APACHE SPARK STRUCTURED STREAMING                     │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   ┌─────────────────────────────┐   ┌─────────────────────────────────┐   │
│   │     JOB 1: INGESTION        │   │     JOB 2: ANALYTICS            │   │
│   │   kafka_to_timescale.py     │   │   sentiment_prediction_job.py   │   │
│   │                             │   │                                 │   │
│   │   SparkSession              │   │   SparkSession                  │   │
│   │   ├─ master: local[*]       │   │   ├─ master: local[*]           │   │
│   │   ├─ app: CRYPTO_VIZ        │   │   ├─ app: CRYPTO_VIZ_Analytics  │   │
│   │   └─ jars: kafka, postgres  │   │   └─ jars: kafka, postgres      │   │
│   │                             │   │                                 │   │
│   │   STREAMS:                  │   │   STREAMS:                      │   │
│   │   ┌──────────────────┐      │   │   ┌────────────────────────┐    │   │
│   │   │ rawarticle       │      │   │   │ rawarticle             │    │   │
│   │   │ readStream       │      │   │   │ readStream             │    │   │
│   │   │ from_json        │──────┼───┼──▶│ explode(cryptos)       │    │   │
│   │   │ withTimestamp    │      │   │   │ withWatermark(2m)      │    │   │
│   │   │ writeStream      │      │   │   │ groupBy(window(3m))    │    │   │
│   │   │ foreachBatch     │      │   │   │   .agg(avg(score))     │    │   │
│   │   │   JDBC append    │      │   │   │ writeStream            │    │   │
│   │   └────────┬─────────┘      │   │   │   JDBC append          │    │   │
│   │            ▼                │   │   └────────┬───────────────┘    │   │
│   │   ┌──────────────────┐      │   │            ▼                    │   │
│   │   │ rawticker        │      │   │   ┌────────────────────────┐    │   │
│   │   │ readStream       │      │   │   │ rawticker              │    │   │
│   │   │ from_json        │──────┼───┼──▶│ readStream             │    │   │
│   │   │ writeStream      │      │   │   │ withWatermark(2m)      │    │   │
│   │   │   JDBC append    │      │   │   │ groupBy(window(3m,30s))│    │   │
│   │   └────────┬─────────┘      │   │   │   .agg(avg,stddev)     │    │   │
│   │            ▼                │   │   │ predict(ma+volatility) │    │   │
│   │   ┌──────────────────┐      │   │   │ writeStream            │    │   │
│   │   │ rawtrade         │      │   │   └────────┬───────────────┘    │   │
│   │   │ (similaire)      │      │   │            ▼                    │   │
│   │   └──────────────────┘      │   │   ┌────────────────────────┐    │   │
│   │                             │   │   │ Tables:                │    │   │
│   │   ┌──────────────────┐      │   │   │ • sentiment_data       │    │   │
│   │   │ rawalert         │      │   │   │ • prediction_data      │    │   │
│   │   │ (similaire)      │      │   │   └────────────────────────┘    │   │
│   │   └──────────────────┘      │   │                                 │   │
│   │                             │   └─────────────────────────────────┘   │
│   │   Tables:                   │                                         │
│   │   • article_data            │                                         │
│   │   • ticker_data             │                                         │
│   │   • trade_data              │                                         │
│   │   • alert_data              │                                         │
│   │                             │                                         │
│   └─────────────────────────────┘                                         │
│                                                                           │
│   CHECKPOINTING: /tmp/spark_checkpoints/{stream_name}/                    │
│   - Fault tolerance                                                       │
│   - Exactly-once semantics                                                │
│   - Recovery automatique                                                  │
│                                                                           │
└────────────────────────────────────────┬──────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TIMESCALEDB STORAGE LAYER                            │
│                    (PostgreSQL 18 + TimescaleDB Extension)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   HYPERTABLES (Time-Series Optimized):                                      │
│                                                                             │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│   │  ticker_data    │  │  trade_data     │  │  article_data               │ │
│   │  ────────────── │  │  ────────────── │  │  ────────────────────────── │ │
│   │  timestamp (PK) │  │  timestamp (PK) │  │  timestamp (PK)             │ │
│   │  pair           │  │  pair           │  │  article_id                 │ │
│   │  last           │  │  price          │  │  title                      │ │
│   │  bid            │  │  volume         │  │  url                        │ │
│   │  ask            │  │  side           │  │  website                    │ │
│   │  volume_24h     │  │                 │  │  summary                    │ │
│   │                 │  │                 │  │  cryptocurrencies_mentione  │ │
│   │  Partition:     │  │  Partition:     │  │  sentiment_score            │ │
│   │  time_bucket    │  │  time_bucket    │  │  sentiment_label            │ │
│   │  (1 hour)       │  │  (1 hour)       │  │                             │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│   │  alert_data     │  │ sentiment_data  │  │  prediction_data            │ │
│   │  ────────────── │  │  ────────────── │  │  ─────────────────────────  │ │
│   │  timestamp (PK) │  │  timestamp (PK) │  │  timestamp (PK)             │ │
│   │  pair           │  │  crypto_symbol  │  │  crypto_symbol              │ │
│   │  last_price     │  │  sentiment_score│  │  predicted_price            │ │
│   │  change_percent │  │  sentiment_label│  │  actual_price               │ │
│   │  threshold      │  │  source         │  │  model_name                 │ │
│   │  alert_type     │  │  confidence     │  │  confidence_interval_low    │ │
│   │                 │  │                 │  │  confidence_interval_high   │ │
│   │  Partition:     │  │  Partition:     │  │                             │ │
│   │  time_bucket    │  │  time_bucket    │  │                             │ │
│   │  (1 day)        │  │  (1 hour)       │  │                             │ │
│   └─────────────────┘  └─────────────────┘  └─────────────────────────────┘ │
│                                                                             │
│   INDEXES:                                                                  │
│   • timestamp DESC (BRIN) - efficace pour time-series                       │
│   • crypto_symbol (BTREE) - recherche rapide par crypto                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DJANGO API LAYER                                    │
│                    (Django 4.2 + Django REST Framework)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                          urls.py                                    │   │
│   │  urlpatterns = [                                                    │   │
│   │      path('api/v1/sentiment/<str:crypto>/historique/',              │   │
│   │           SentimentHistoriqueView.as_view()),                       │   │
│   │      path('api/v1/prix/<str:crypto>/historique/',                   │   │
│   │           PrixHistoriqueView.as_view()),                            │   │
│   │      path('api/v1/prix/<str:crypto>/temps_reel/',                   │   │
│   │           PrixTempsReelView.as_view()),                             │   │
│   │      path('api/v1/predictions/<str:crypto>/',                       │   │
│   │           PredictionsView.as_view()),                               │   │
│   │      path('api/v1/articles/<str:crypto>/',                          │   │
│   │           ArticlesView.as_view()),                                  │   │
│   │  ]                                                                  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                       timescale_client.py                           │   │
│   │                                                                     │   │
│   │  class TimescaleClient:                                             │   │
│   │      def query_sentiment_historique(self, crypto, periode):         │   │
│   │          # SQL optimisé TimescaleDB                                 │   │
│   │          sql = """                                                  │   │
│   │              SELECT time_bucket('1 hour', timestamp) as bucket,     │   │
│   │                     AVG(sentiment_score) as avg_score               │   │
│   │              FROM sentiment_data                                    │   │
│   │              WHERE crypto_symbol = %s                               │   │
│   │                AND timestamp > NOW() - INTERVAL %s                  │   │
│   │              GROUP BY bucket                                        │   │
│   │              ORDER BY bucket DESC                                   │   │
│   │          """                                                        │   │
│   │          return self.execute(sql, [crypto, periode])                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
## Flux de données détaillé

### 1. Article RSS → Sentiment

```
CoinDesk RSS
    │
    ▼
┌─────────────────┐
│ Article Scraper │ ◀── parse RSS (feedparser)
│                 │ ◀── extract content (BeautifulSoup)
│                 │ ◀── sentiment analysis (TextBlob)
│                 │     polarity [-1,1] → score [0,1]
│                 │     label: >0.6=positive, <0.4=negative
└────────┬────────┘
         │
         ▼ JSON
┌─────────────────┐
│ Kafka           │ ◀── topic: rawarticle
│                 │ ◀── key: source (CoinDesk)
│                 │ ◀── partition: hash(key)
└────────┬────────┘
         │
         ▼ DataFrame
┌─────────────────┐
│ Spark Ingestion │ ◀── readStream
│                 │ ◀── from_json (schema ARTICLE_SCHEMA)
│                 │ ◀── nested extract: sentiment.score
│                 │ ◀── writeStream (foreachBatch JDBC)
└────────┬────────┘
         │
         ▼ SQL INSERT
┌─────────────────┐
│ TimescaleDB     │ ◀── table: article_data
└────────┬────────┘
         │
         ▼ DataFrame
┌─────────────────┐
│ Spark Analytics │ ◀── readStream (rawarticle)
│                 │ ◀── explode(cryptocurrencies_mentioned)
│                 │ ◀── withWatermark(2 minutes)
│                 │ ◀── window(3 minutes)
│                 │ ◀── groupBy(crypto_symbol, window)
│                 │ ◀── agg(avg(sentiment_score))
│                 │ ◀── writeStream (foreachBatch JDBC)
└────────┬────────┘
         │
         ▼ SQL INSERT
┌─────────────────┐
│ TimescaleDB     │ ◀── table: sentiment_data
└────────┬────────┘
         │
         ▼ HTTP GET
┌─────────────────┐
│ Django API      │ ◀── /api/v1/sentiment/{crypto}/historique/
│                 │ ◀── time_bucket query
└─────────────────┘
```
### 2. Prix Kraken → Prédiction

```
Kraken WebSocket
    │
    ▼
┌─────────────────┐
│ Kraken Producer │ ◀── ws connection
│                 │ ◀── parse ticker message
│                 │ ◀── detect price change > 0.5%
│                 │ ◀── produce to rawticker / rawalert
└────────┬────────┘
         │
         ▼ JSON
┌─────────────────┐
│ Kafka           │ ◀── topic: rawticker / rawalert
└────────┬────────┘
         │
         ▼ DataFrame
┌─────────────────┐
│ Spark Ingestion │ ◀── readStream
│                 │ ◀── from_json (schema TICKER_SCHEMA)
│                 │ ◀── writeStream (foreachBatch JDBC)
└────────┬────────┘
         │
         ▼ SQL INSERT
┌─────────────────┐
│ TimescaleDB     │ ◀── table: ticker_data / alert_data
└────────┬────────┘
         │
         ▼ DataFrame
┌─────────────────┐
│ Spark Analytics │ ◀── readStream (rawticker)
│                 │ ◀── split(pair, '/')[0] → crypto_symbol
│                 │ ◀── withWatermark(2 minutes)
│                 │ ◀── window(3 minutes, 30 seconds slide)
│                 │ ◀── groupBy(crypto_symbol, window)
│                 │ ◀── agg(avg, stddev, min, max)
│                 │ ◀── predict: ma ± volatility
│                 │ ◀── writeStream (foreachBatch JDBC)
└────────┬────────┘
         │
         ▼ SQL INSERT
┌─────────────────┐
│ TimescaleDB     │ ◀── table: prediction_data
└────────┬────────┘
         │
         ▼ HTTP GET
┌─────────────────┐
│ Django API      │ ◀── /api/v1/predictions/{crypto}/
│                 │ ◀── latest prediction query
└─────────────────┘
```

## Patterns architecturaux

### 1. Producer-Consumer Pattern
- **Producers** : Article Scraper, Kraken Producer
- **Broker** : Kafka topics
- **Consumers** : Spark Streaming jobs

### 2. Lambda Architecture (Simplifié)
- **Batch** : Articles RSS toutes les 5 minutes
- **Speed** : Prix Kraken en temps réel
- **Serving** : Django API unifiée

### 3. Event-Driven Architecture
- Kafka comme event bus central
- Spark micro-batches pour traitement
- Checkpoints pour fault tolerance

### 4. Micro-batch Processing
- Spark Structured Streaming
- Trigger par micro-batch (défaut)
- Windowing temporel pour agrégations

### 5. CQRS (Command Query Responsibility Segregation)
- **Commands** : Spark écrit dans TimescaleDB
- **Queries** : Django lit depuis TimescaleDB
- Séparation des modèles lecture/écriture

## Flux temporel

```
Temps
  │
  │   T+0s    Article publié sur CoinDesk
  │           │
  │   T+5s    Scraper détecte article (cycle 5min)
  │           │
  │   T+6s    Sentiment analysé (TextBlob ~10ms)
  │           │
  │   T+7s    Message produit vers Kafka
  │           │
  │   T+8s    Spark ingère message (micro-batch)
  │           │
  │   T+9s    Article inséré dans article_data
  │           │
  │   T+10s   Spark Analytics window trigger
  │           │
  │   T+3min  Window fermée, agrégation calculée
  │           │
  │   T+3min+ sentiment_data mis à jour
  │           │
  │   T+any   API répond avec données agrégées
  │
  ▼
```

---

**Suite** : [02-data-producers.md](./02-data-producers.md) pour le détail des producteurs de données.
