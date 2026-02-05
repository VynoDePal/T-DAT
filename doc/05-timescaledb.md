# TimescaleDB - Stockage des Séries Temporelles

## Vue d'ensemble

TimescaleDB est une extension PostgreSQL spécialisée pour les **séries temporelles**. Elle offre des performances supérieures pour les données timestampées avec partitioning automatique et indexation optimisée.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TIMESCALEDB LAYER                               │
│                   (PostgreSQL 18 + TimescaleDB Extension)                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                    HYPERTABLES (Time-Series)                        │ │
│   │                                                                     │ │
│   │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │ │
│   │  │ticker_data  │ │trade_data   │ │article_data │ │alert_data   │   │ │
│   │  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤   │ │
│   │  │timestamp(PK)│ │timestamp(PK)│ │timestamp(PK)│ │timestamp(PK)│   │ │
│   │  │pair         │ │pair         │ │article_id   │ │pair         │   │ │
│   │  │last         │ │price        │ │title        │ │last_price   │   │ │
│   │  │bid          │ │volume       │ │url          │ │change_pct   │   │ │
│   │  │ask          │ │side         │ │website      │ │threshold    │   │ │
│   │  │volume_24h   │ │             │ │summary      │ │alert_type   │   │ │
│   │  │             │ │             │ │sentiment_*  │ │             │   │ │
│   │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │ │
│   │                                                                     │ │
│   │  ┌─────────────┐ ┌─────────────┐                                    │ │
│   │  │sentiment_   │ │prediction_  │                                    │ │
│   │  │data         │ │data         │                                    │ │
│   │  ├─────────────┤ ├─────────────┤                                    │ │
│   │  │timestamp(PK)│ │timestamp(PK)│                                    │ │
│   │  │crypto_symbol│ │crypto_symbol│                                    │ │
│   │  │sentiment_*  │ │predicted_pr │                                    │ │
│   │  │confidence   │ │confidence_* │                                    │ │
│   │  └─────────────┘ └─────────────┘                                    │ │
│   │                                                                     │ │
│   │  CHUNKS (Partitionnement automatique par temps):                    │ │
│   │  • Chunk actif: données récentes (7 derniers jours)               │ │
│   │  • Chunks compressés: données anciennes compressées                 │ │
│   │                                                                     │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Architecture de stockage

### Hypertables vs Tables standard

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMPARISON: TABLE vs HYPERTABLE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   TABLE STANDARD PostgreSQL                                             │
│   ┌─────────────────────────────────────────┐                           │
│   │  timestamp │ pair    │ price            │                           │
│   ├─────────────────────────────────────────┤                           │
│   │  T1       │ BTC/USD │ 50000           │ ← 1 table = 1 fichier   │
│   │  T2       │ ETH/USD │ 3000            │                           │
│   │  T3       │ BTC/USD │ 50100           │ ← Insertions lentes       │
│   │  T4       │ ...     │ ...             │   (index maintenance)     │
│   └─────────────────────────────────────────┘                           │
│                                                                         │
│   HYPERTABLE TimescaleDB                                                │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Chunk 1 (Jour 1)    │ Chunk 2 (Jour 2)    │ Chunk 3 (Jour 3)  │   │
│   │  ┌──────────────┐    │ ┌──────────────┐    │ ┌──────────────┐  │   │
│   │  │ timestamp    │    │ │ timestamp    │    │ │ timestamp    │  │   │
│   │  │ T1..T1000    │    │ │ T1001..T2000 │    │ │ T2001..T3000 │  │   │
│   │  └──────────────┘    │ └──────────────┘    │ └──────────────┘  │   │
│   │       │              │       │              │       │           │   │
│   │   ┌───┴───┐          │   ┌───┴───┐          │   ┌───┴───┐       │   │
│   │   │Index  │          │   │Index  │          │   │Index  │       │   │
│   │   │BRIN   │          │   │BRIN   │          │   │BRIN   │       │   │
│   │   └───────┘          │   └───────┘          │   └───────┘       │   │
│   │                     │                      │                      │   │
│   │  • Insertions rapides (pas de lock sur tout l'index)             │   │
│   │  • Queries temporelles optimisées (pruning de chunks)            │   │
│   │  • Compression automatique des anciens chunks                     │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Schéma des tables

### 1. ticker_data (Prix temps réel)

```sql
-- Création table standard
CREATE TABLE ticker_data (
    timestamp TIMESTAMPTZ NOT NULL,
    pair VARCHAR(20) NOT NULL,
    last DOUBLE PRECISION NOT NULL,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    volume_24h DOUBLE PRECISION
);

-- Conversion en hypertable
SELECT create_hypertable('ticker_data', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- Index pour recherches rapides par crypto
CREATE INDEX idx_ticker_pair ON ticker_data (pair, timestamp DESC);

-- Commentaires
COMMENT ON TABLE ticker_data IS 'Données de prix temps réel depuis Kraken';
```

### 2. trade_data (Transactions)

```sql
CREATE TABLE trade_data (
    timestamp TIMESTAMPTZ NOT NULL,
    pair VARCHAR(20) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    side VARCHAR(1) NOT NULL  -- 'b' ou 's'
);

SELECT create_hypertable('trade_data', 'timestamp', chunk_time_interval => INTERVAL '1 hour');
CREATE INDEX idx_trade_pair ON trade_data (pair, timestamp DESC);
```

### 3. article_data (Articles avec sentiment)

```sql
CREATE TABLE article_data (
    timestamp TIMESTAMPTZ NOT NULL,
    article_id VARCHAR(500) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    website VARCHAR(100) NOT NULL,
    summary TEXT,
    cryptocurrencies_mentioned TEXT[],
    sentiment_score DOUBLE PRECISION,
    sentiment_label VARCHAR(20)
);

SELECT create_hypertable('article_data', 'timestamp', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_article_website ON article_data (website, timestamp DESC);
CREATE INDEX idx_article_sentiment ON article_data (sentiment_label, timestamp DESC);
```

### 4. alert_data (Alertes prix)

```sql
CREATE TABLE alert_data (
    timestamp TIMESTAMPTZ NOT NULL,
    pair VARCHAR(20) NOT NULL,
    last_price DOUBLE PRECISION NOT NULL,
    change_percent DOUBLE PRECISION NOT NULL,
    threshold DOUBLE PRECISION NOT NULL,
    alert_type VARCHAR(20) NOT NULL  -- 'PRICE_UP' ou 'PRICE_DOWN'
);

SELECT create_hypertable('alert_data', 'timestamp', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_alert_pair ON alert_data (pair, timestamp DESC);
```

### 5. sentiment_data (Sentiment agrégé)

```sql
CREATE TABLE sentiment_data (
    timestamp TIMESTAMPTZ NOT NULL,
    crypto_symbol VARCHAR(50) NOT NULL,
    sentiment_score DOUBLE PRECISION NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    source VARCHAR(100) NOT NULL,
    confidence DOUBLE PRECISION
);

SELECT create_hypertable('sentiment_data', 'timestamp', chunk_time_interval => INTERVAL '1 hour');
CREATE INDEX idx_sentiment_crypto ON sentiment_data (crypto_symbol, timestamp DESC);
CREATE INDEX idx_sentiment_label ON sentiment_data (sentiment_label, timestamp DESC);
```

### 6. prediction_data (Prédictions de prix)

```sql
CREATE TABLE prediction_data (
    timestamp TIMESTAMPTZ NOT NULL,
    crypto_symbol VARCHAR(50) NOT NULL,
    predicted_price DOUBLE PRECISION NOT NULL,
    actual_price DOUBLE PRECISION,
    model_name VARCHAR(50) NOT NULL,
    confidence_interval_low DOUBLE PRECISION,
    confidence_interval_high DOUBLE PRECISION
);

SELECT create_hypertable('prediction_data', 'timestamp', chunk_time_interval => INTERVAL '1 hour');
CREATE INDEX idx_prediction_crypto ON prediction_data (crypto_symbol, timestamp DESC);
```

## Fonctions TimescaleDB

### time_bucket (Agrégation temporelle)

```sql
-- Agrège les données en buckets de 1 heure
SELECT 
    time_bucket('1 hour', timestamp) as bucket,
    pair,
    AVG(last) as avg_price,
    MIN(last) as min_price,
    MAX(last) as max_price
FROM ticker_data
WHERE pair = 'XBT/USD'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY bucket, pair
ORDER BY bucket DESC;

-- Résultat:
-- bucket              │ pair    │ avg_price │ min_price │ max_price
-- ─────────────────────┼─────────┼───────────┼───────────┼───────────
-- 2024-01-15 14:00:00 │ XBT/USD │  99950.50 │  99800.00 │ 100100.00
-- 2024-01-15 13:00:00 │ XBT/USD │  99800.00 │  99600.00 │  99900.00
```

### last / first (Valeurs d'agrégation)

```sql
-- Dernier prix par paire (plus rapide que ORDER BY + LIMIT)
SELECT 
    pair,
    last(last, timestamp) as latest_price,
    last(timestamp, timestamp) as latest_time
FROM ticker_data
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY pair;
```

### continuous aggregates (Vues matérialisées)

```sql
-- Créer une vue agrégée pour les statistiques horaires
CREATE MATERIALIZED VIEW ticker_hourly_stats
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) as bucket,
    pair,
    AVG(last) as avg_price,
    MIN(last) as min_price,
    MAX(last) as max_price,
    AVG(volume_24h) as avg_volume
FROM ticker_data
GROUP BY bucket, pair;

-- Rafraîchissement automatique toutes les heures
SELECT add_continuous_aggregate_policy('ticker_hourly_stats',
    start_offset => INTERVAL '1 month',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

## Requêtes API (utilisées par Django)

### Sentiment historique

```sql
-- API: GET /api/v1/sentiment/{crypto}/historique/?periode=7d
SELECT 
    time_bucket('1 hour', timestamp) as bucket,
    AVG(sentiment_score) as avg_sentiment,
    COUNT(*) as article_count,
    MODE() WITHIN GROUP (ORDER BY sentiment_label) as dominant_label
FROM sentiment_data
WHERE crypto_symbol ILIKE '%bitcoin%'
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY bucket
ORDER BY bucket DESC;
```

### Prix temps réel

```sql
-- API: GET /api/v1/prix/{crypto}/temps_reel/
SELECT 
    pair,
    last,
    bid,
    ask,
    volume_24h,
    timestamp
FROM ticker_data
WHERE pair LIKE '%BTC%'
ORDER BY timestamp DESC
LIMIT 1;
```

### Historique des prix

```sql
-- API: GET /api/v1/prix/{crypto}/historique/
SELECT 
    time_bucket('5 minutes', timestamp) as bucket,
    pair,
    AVG(last) as avg_price,
    MIN(last) as min_price,
    MAX(last) as max_price
FROM ticker_data
WHERE pair = 'XBT/USD'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY bucket, pair
ORDER BY bucket DESC;
```

### Prédictions

```sql
-- API: GET /api/v1/predictions/{crypto}/
SELECT 
    timestamp,
    crypto_symbol,
    predicted_price,
    actual_price,
    confidence_interval_low,
    confidence_interval_high,
    (confidence_interval_high - confidence_interval_low) as confidence_range
FROM prediction_data
WHERE crypto_symbol = 'BTC'
ORDER BY timestamp DESC
LIMIT 100;
```

## Administration

### Connexion

```bash
# Docker
docker exec -it t-dat-timescaledb-1 psql -U postgres -d crypto_viz_ts

# Local (port 15432)
psql -h localhost -p 15432 -U postgres -d crypto_viz_ts
```

### Commandes utiles

```sql
-- Lister les hypertables
SELECT * FROM timescaledb_information.hypertables;

-- Lister les chunks
SELECT * FROM timescaledb_information.chunks 
WHERE hypertable_name = 'ticker_data'
ORDER BY range_start DESC;

-- Taille des tables
SELECT 
    hypertable_name,
    pg_size_pretty(total_bytes) as size
FROM timescaledb_information.hypertable_compression_stats
ORDER BY total_bytes DESC;

-- Statistiques d'insertion
SELECT 
    relname as table_name,
    n_tup_ins as insertions,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables
WHERE relname LIKE '%data'
ORDER BY n_tup_ins DESC;
```

### Maintenance

```sql
-- Compression manuelle des anciens chunks
SELECT compress_chunk(i.chunk_name)
FROM timescaledb_information.chunks i
WHERE i.hypertable_name = 'ticker_data'
  AND i.range_end < NOW() - INTERVAL '7 days';

-- Décompression si besoin d'accès
SELECT decompress_chunk(i.chunk_name)
FROM timescaledb_information.chunks i
WHERE i.chunk_name = '_hyper_ticker_data_1_1_chunk';

-- Supprimer vieux chunks
SELECT drop_chunks('ticker_data', INTERVAL '30 days');
```

### Sauvegarde et restauration

```bash
# Backup
docker exec t-dat-timescaledb-1 pg_dump -U postgres crypto_viz_ts > backup.sql

# Restore
docker exec -i t-dat-timescaledb-1 psql -U postgres crypto_viz_ts < backup.sql
```

## Performance

### Index recommandés

| Table | Index | Usage |
|-------|-------|-------|
| ticker_data | (pair, timestamp DESC) | Requêtes par crypto |
| trade_data | (pair, timestamp DESC) | Historique trades |
| article_data | (website, timestamp DESC) | Articles par source |
| sentiment_data | (crypto_symbol, timestamp DESC) | API sentiment |
| prediction_data | (crypto_symbol, timestamp DESC) | API prédictions |

### Optimisations

```sql
-- Partitionnement par crypto (optionnel pour très gros volumes)
-- Créer une hypertable avec partitionnement spatial
SELECT create_hypertable('ticker_data', 'timestamp', 
    partitioning_column => 'pair',
    number_partitions => 8,
    chunk_time_interval => INTERVAL '1 hour');

-- Compression automatique après 7 jours
ALTER TABLE ticker_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'pair'
);

SELECT add_compression_policy('ticker_data', INTERVAL '7 days');
```

---

**Suite** : [06-backend-api.md](./06-backend-api.md) pour l'API Django.
