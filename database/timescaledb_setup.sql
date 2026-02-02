-- Script de configuration de TimescaleDB pour CRYPTO VIZ
-- Crée les tables de séries temporelles et les hypertables

-- Créer la base de données (à exécuter en tant que superuser)
-- CREATE DATABASE crypto_viz_ts;
-- \c crypto_viz_ts
-- CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ==============================================================================
-- Table pour les données de ticker (prix en temps réel)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS ticker_data (
    timestamp TIMESTAMPTZ NOT NULL,
    pair VARCHAR(20) NOT NULL,
    last DOUBLE PRECISION NOT NULL,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    volume_24h DOUBLE PRECISION
);

-- Convertir en hypertable
SELECT create_hypertable('ticker_data', 'timestamp', if_not_exists => TRUE);

-- Index pour améliorer les performances des requêtes
CREATE INDEX IF NOT EXISTS idx_ticker_pair_timestamp ON ticker_data (pair, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ticker_timestamp ON ticker_data (timestamp DESC);


-- ==============================================================================
-- Table pour les données de trade (transactions)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS trade_data (
    timestamp TIMESTAMPTZ NOT NULL,
    pair VARCHAR(20) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    side VARCHAR(1) NOT NULL -- 'b' for buy, 's' for sell
);

-- Convertir en hypertable
SELECT create_hypertable('trade_data', 'timestamp', if_not_exists => TRUE);

-- Index
CREATE INDEX IF NOT EXISTS idx_trade_pair_timestamp ON trade_data (pair, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trade_side ON trade_data (side, timestamp DESC);


-- ==============================================================================
-- Table pour les données d'articles
-- ==============================================================================
CREATE TABLE IF NOT EXISTS article_data (
    timestamp TIMESTAMPTZ NOT NULL,
    article_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    website VARCHAR(100),
    summary TEXT,
    cryptocurrencies_mentioned TEXT[],
    sentiment_score DOUBLE PRECISION,
    sentiment_label VARCHAR(20)
);

-- Convertir en hypertable
SELECT create_hypertable('article_data', 'timestamp', if_not_exists => TRUE);

-- Index
CREATE INDEX IF NOT EXISTS idx_article_timestamp ON article_data (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_article_cryptos ON article_data USING GIN (cryptocurrencies_mentioned);
CREATE INDEX IF NOT EXISTS idx_article_sentiment ON article_data (sentiment_label, timestamp DESC);


-- ==============================================================================
-- Table pour les données d'alertes
-- ==============================================================================
CREATE TABLE IF NOT EXISTS alert_data (
    timestamp TIMESTAMPTZ NOT NULL,
    pair VARCHAR(20) NOT NULL,
    last_price DOUBLE PRECISION NOT NULL,
    change_percent DOUBLE PRECISION NOT NULL,
    threshold DOUBLE PRECISION NOT NULL,
    alert_type VARCHAR(20) NOT NULL -- 'PRICE_UP', 'PRICE_DOWN'
);

-- Convertir en hypertable
SELECT create_hypertable('alert_data', 'timestamp', if_not_exists => TRUE);

-- Index
CREATE INDEX IF NOT EXISTS idx_alert_pair_timestamp ON alert_data (pair, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alert_type ON alert_data (alert_type, timestamp DESC);


-- ==============================================================================
-- Table pour les données de sentiment (agrégées par Spark)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS sentiment_data (
    timestamp TIMESTAMPTZ NOT NULL,
    crypto_symbol VARCHAR(50) NOT NULL,
    sentiment_score DOUBLE PRECISION NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    source VARCHAR(100) NOT NULL,
    confidence DOUBLE PRECISION
);

-- Convertir en hypertable
SELECT create_hypertable('sentiment_data', 'timestamp', if_not_exists => TRUE);

-- Index
CREATE INDEX IF NOT EXISTS idx_sentiment_crypto_timestamp ON sentiment_data (crypto_symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sentiment_label ON sentiment_data (sentiment_label, timestamp DESC);


-- ==============================================================================
-- Table pour les données de prédiction (générées par Spark)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS prediction_data (
    timestamp TIMESTAMPTZ NOT NULL,
    crypto_symbol VARCHAR(50) NOT NULL,
    predicted_price DOUBLE PRECISION NOT NULL,
    actual_price DOUBLE PRECISION,
    model_name VARCHAR(50) NOT NULL,
    confidence_interval_low DOUBLE PRECISION,
    confidence_interval_high DOUBLE PRECISION
);

-- Convertir en hypertable
SELECT create_hypertable('prediction_data', 'timestamp', if_not_exists => TRUE);

-- Index
CREATE INDEX IF NOT EXISTS idx_prediction_crypto_timestamp ON prediction_data (crypto_symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_prediction_model ON prediction_data (model_name, timestamp DESC);


-- ==============================================================================
-- Politiques de rétention (optionnel - conserver 90 jours de données)
-- ==============================================================================
-- Supprimer automatiquement les données de plus de 90 jours
SELECT add_retention_policy('ticker_data', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('trade_data', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('article_data', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('alert_data', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('sentiment_data', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('prediction_data', INTERVAL '90 days', if_not_exists => TRUE);


-- ==============================================================================
-- Vues matérialisées pour des agrégations rapides (optionnel)
-- ==============================================================================

-- Vue pour le sentiment horaire moyen par crypto
CREATE MATERIALIZED VIEW IF NOT EXISTS sentiment_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    crypto_symbol,
    AVG(sentiment_score) AS avg_sentiment,
    COUNT(*) AS sample_count
FROM sentiment_data
GROUP BY bucket, crypto_symbol;

-- Rafraîchissement automatique toutes les heures
SELECT add_continuous_aggregate_policy('sentiment_hourly',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);


-- Vue pour les prix OHLC (Open, High, Low, Close) par heure
CREATE MATERIALIZED VIEW IF NOT EXISTS ticker_ohlc_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    pair,
    FIRST(last, timestamp) AS open,
    MAX(last) AS high,
    MIN(last) AS low,
    LAST(last, timestamp) AS close,
    AVG(volume_24h) AS avg_volume
FROM ticker_data
GROUP BY bucket, pair;

-- Rafraîchissement automatique
SELECT add_continuous_aggregate_policy('ticker_ohlc_hourly',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);


-- ==============================================================================
-- Permissions (ajuster selon vos besoins)
-- ==============================================================================
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO crypto_viz_user;


-- ==============================================================================
-- Statistiques et informations
-- ==============================================================================
-- Pour voir les hypertables créées:
-- SELECT * FROM timescaledb_information.hypertables;

-- Pour voir les chunks:
-- SELECT * FROM timescaledb_information.chunks;

-- Pour voir l'espace disque utilisé:
-- SELECT * FROM timescaledb_information.hypertable_detailed_size('ticker_data');

COMMENT ON TABLE ticker_data IS 'Données de prix en temps réel des crypto-monnaies';
COMMENT ON TABLE trade_data IS 'Transactions individuelles d''achat/vente';
COMMENT ON TABLE article_data IS 'Articles de presse crypto avec analyse de sentiment';
COMMENT ON TABLE alert_data IS 'Alertes basées sur les variations de prix';
COMMENT ON TABLE sentiment_data IS 'Analyse de sentiment agrégée par crypto';
COMMENT ON TABLE prediction_data IS 'Prédictions de prix générées par ML';

COMMIT;
