# Apache Spark Structured Streaming

## Vue d'ensemble

Apache Spark Structured Streaming est la couche de **traitement temps réel** du pipeline CRYPTO VIZ. Il consomme les messages Kafka, les transforme et les écrit dans TimescaleDB.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SPARK STRUCTURED STREAMING                           │
│                           (Apache Spark 3.5.0)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────┐   ┌─────────────────────────────┐   │
│   │    JOB 1: INGESTION         │   │    JOB 2: ANALYTICS         │   │
│   │    kafka_to_timescale.py    │   │    sentiment_prediction.py    │   │
│   │                             │   │                             │   │
│   │  4 Streams parallèles:      │   │  2 Streams analytiques:       │   │
│   │  ┌─────────────────────┐    │   │  ┌─────────────────────┐      │   │
│   │  │ rawarticle Stream   │    │   │  │ Sentiment Stream    │      │   │
│   │  │ ├─ from_json        │    │   │  │ ├─ from_json        │      │   │
│   │  │ ├─ nested extract     │──┐ │   │  │ ├─ explode(cryptos) │      │   │
│   │  │ └─ JDBC write         │  │ │   │  │ ├─ window(3m)       │      │   │
│   │  │                       │  │ │   │  │ ├─ agg(avg(score))  │      │   │
│   │  │ rawticker Stream      │  │ │   │  │ └─ JDBC write       │      │   │
│   │  │ ├─ from_json          │  │ │   │  └─────────────────────┘      │   │
│   │  │ ├─ timestamp conv     │─┐│ │   │                               │   │
│   │  │ └─ JDBC write         │ ││ │   │  ┌─────────────────────┐      │   │
│   │  │                       │ ││ │   │  │ Prediction Stream   │      │   │
│   │  │ rawtrade Stream       │ ││ │   │  │ ├─ from_json        │      │   │
│   │  │ ├─ from_json          │─┼┘ │   │  │ ├─ window(3m,30s)   │      │   │
│   │  │ └─ JDBC write         │ │  │   │  │ ├─ agg(avg,stddev)  │      │   │
│   │  │                       │ │  │   │  │ └─ JDBC write       │      │   │
│   │  │ rawalert Stream       │ │  │   │  └─────────────────────┘      │   │
│   │  │ └─ JDBC write         │─┘  │   │                               │   │
│   │  └─────────────────────┘     │   └─────────────────────────────┘   │
│   │                              │                                         │
│   │  Checkpoint: /tmp/spark_checkpoints/{topic}/                        │
│   │                              │                                         │
│   └─────────────────────────────┘                                         │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Architecture Spark

### SparkSession Configuration

```python
from pyspark.sql import SparkSession
import config

def create_spark_session():
    """Crée et configure la session Spark."""
    
    # Recherche des JARs locaux
    jars_dir = os.path.join(os.path.dirname(__file__), "jars")
    jar_files = glob.glob(os.path.join(jars_dir, "*.jar"))
    jars_path = ",".join(jar_files)
    
    return SparkSession.builder \
        .appName(config.SPARK_APP_NAME) \  # "CRYPTO_VIZ_Streaming"
        .master(config.SPARK_MASTER) \     # "local[*]" - tous les cores
        .config("spark.jars", jars_path) \  # JARs Kafka + PostgreSQL
        .config("spark.sql.streaming.checkpointLocation", config.CHECKPOINT_LOCATION) \
        .config("spark.sql.streaming.schemaInference", "false") \
        .getOrCreate()

# Configuration JVM
spark.sparkContext.setLogLevel("WARN")  # Réduire logs
```

### Dépendances JARs

| JAR | Version | Usage |
|-----|---------|-------|
| `spark-sql-kafka-0-10_2.12-3.5.0.jar` | 3.5.0 | Connecteur Kafka pour Spark SQL |
| `kafka-clients-3.4.1.jar` | 3.4.1 | Client Kafka |
| `postgresql-42.7.1.jar` | 42.7.1 | Driver JDBC PostgreSQL/TimescaleDB |
| `commons-pool2-2.11.1.jar` | 2.11.1 | Pool de connexions (dépendance) |
| `spark-token-provider-kafka-0-10_2.12-3.5.0.jar` | 3.5.0 | Authentification Kafka |

## Job 1: kafka_to_timescale.py

### Objectif
Ingestion des 4 topics Kafka vers TimescaleDB avec transformation minimale.

### Flux rawarticle

```python
def process_article_stream(spark):
    """
    Traite le stream rawarticle.
    """
    # 1. Lire le stream Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", config.KAFKA_TOPICS['ARTICLE']) \  # "rawarticle"
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # 2. Parser le JSON avec schéma
    from spark_jobs.schemas import ARTICLE_SCHEMA
    
    article_df = kafka_df \
        .select(from_json(col("value").cast("string"), ARTICLE_SCHEMA).alias("data")) \
        .select("data.*")  # Aplatit la structure nested
    
    # 3. Transformation des timestamps
    from pyspark.sql.functions import current_timestamp
    
    article_df = article_df \
        .withColumn("timestamp", current_timestamp())
    
    # 4. Extraction des champs nested
    from pyspark.sql.functions import col
    
    transformed_df = article_df.select(
        col("timestamp"),
        col("id").alias("article_id"),
        col("title"),
        col("url"),
        col("website"),
        col("summary"),
        col("cryptocurrencies_mentioned"),
        col("sentiment.score").alias("sentiment_score"),
        col("sentiment.label").alias("sentiment_label")
    )
    
    # 5. Écriture TimescaleDB
    def write_batch(batch_df, batch_id):
        if batch_df.count() > 0:
            batch_df.write \
                .format("jdbc") \
                .option("url", config.TIMESCALE_JDBC_URL) \
                .option("dbtable", "article_data") \
                .option("user", config.TIMESCALE_CONFIG['user']) \
                .option("password", config.TIMESCALE_CONFIG['password']) \
                .option("driver", "org.postgresql.Driver") \
                .mode("append") \
                .save()
            print(f"Batch {batch_id}: {batch_df.count()} rows écrites")
    
    query = transformed_df.writeStream \
        .foreachBatch(write_batch) \
        .option("checkpointLocation", f"{config.CHECKPOINT_LOCATION}/article") \
        .start()
    
    return query
```

### Flux rawticker

```python
def process_ticker_stream(spark):
    """
    Traite le stream rawticker.
    """
    # Schéma TICKER_SCHEMA défini dans schemas.py
    from spark_jobs.schemas import TICKER_SCHEMA
    from pyspark.sql.functions import from_unixtime
    from pyspark.sql.types import TimestampType
    
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("subscribe", "rawticker") \
        .load()
    
    # Parsing et conversion timestamp
    ticker_df = kafka_df \
        .select(from_json(col("value").cast("string"), TICKER_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", from_unixtime(col("timestamp")).cast(TimestampType())) \
        .select(
            col("timestamp"),
            col("pair"),
            col("last"),
            col("bid"),
            col("ask"),
            col("volume_24h")
        )
    
    # Écriture
    query = write_to_timescale(ticker_df, "ticker_data", 
                                f"{config.CHECKPOINT_LOCATION}/ticker")
    return query
```

### Pattern d'écriture JDBC (foreachBatch)

```python
def write_to_timescale(df, table_name, checkpoint_path):
    """
    Pattern générique pour écrire un stream vers TimescaleDB.
    """
    def write_batch(batch_df, batch_id):
        """
        Fonction appelée pour chaque micro-batch.
        """
        count = batch_df.count()
        
        if count > 0:
            print(f"[DEBUG] {table_name} - Batch {batch_id}: {count} rows")
            
            batch_df.write \
                .format("jdbc") \
                .option("url", config.TIMESCALE_JDBC_URL) \
                .option("dbtable", table_name) \
                .option("user", config.TIMESCALE_CONFIG['user']) \
                .option("password", config.TIMESCALE_CONFIG['password']) \
                .option("driver", "org.postgresql.Driver") \
                .mode("append") \
                .save()
            
            print(f"✅ Batch {batch_id}: {count} rows écrites dans {table_name}")
    
    return df.writeStream \
        .foreachBatch(write_batch) \
        .option("checkpointLocation", checkpoint_path) \
        .start()
```

## Job 2: sentiment_prediction_job.py

### Objectif
Analyse avancée : agrégation de sentiment et prédictions de prix.

### Flux d'analyse de sentiment

```python
from pyspark.sql.functions import (
    from_json, col, current_timestamp, window, avg, 
    explode, expr
)
from pyspark.sql.types import DoubleType

def process_sentiment_from_articles(spark):
    """
    Agrège le sentiment par crypto sur des fenêtres temporelles.
    """
    # 1. Lecture topic rawarticle
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("subscribe", "rawarticle") \
        .load()
    
    # 2. Parsing
    from spark_jobs.schemas import ARTICLE_SCHEMA
    
    article_df = kafka_df \
        .select(from_json(col("value").cast("string"), ARTICLE_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", current_timestamp())
    
    # 3. Transformation clé : explode cryptocurrencies_mentioned
    # 1 article avec ["bitcoin", "btc"] → 2 lignes
    exploded_df = article_df.select(
        col("timestamp"),
        explode(col("cryptocurrencies_mentioned")).alias("crypto_symbol"),
        col("sentiment.score").alias("sentiment_score"),
        col("sentiment.label").alias("sentiment_label"),
        col("website").alias("source")
    )
    
    # 4. Ajout watermark (gestion du retard)
    # Accepte données jusqu'à 2 minutes de retard
    watermarked_df = exploded_df \
        .withWatermark("timestamp", "2 minutes")
    
    # 5. Agrégation par fenêtre temporelle
    # Regroupement par crypto et fenêtre de 3 minutes
    windowed_df = watermarked_df \
        .groupBy(
            window(col("timestamp"), "3 minutes"),  # Tumbling window
            col("crypto_symbol")
        ) \
        .agg(
            avg("sentiment_score").alias("avg_sentiment_score"),
            avg(col("sentiment_score").cast(DoubleType())).alias("avg_confidence")
        )
    
    # 6. Transformation finale
    result_df = windowed_df.select(
        col("window.end").alias("timestamp"),
        col("crypto_symbol"),
        col("avg_sentiment_score").alias("sentiment_score"),
        # Classification du sentiment
        expr("CASE WHEN avg_sentiment_score > 0.6 THEN 'positive' " +
             "WHEN avg_sentiment_score < 0.4 THEN 'negative' " +
             "ELSE 'neutral' END").alias("sentiment_label"),
        expr("'aggregated_articles'").alias("source"),
        col("avg_confidence").alias("confidence")
    )
    
    # 7. Écriture
    query = write_to_timescale(
        result_df,
        "sentiment_data",
        "/tmp/spark_checkpoints_sentiment/sentiment"
    )
    
    return query
```

### Flux de prédiction de prix

```python
from pyspark.sql.functions import (
    stddev, min as spark_min, max as spark_max, split, expr
)

def process_price_predictions(spark):
    """
    Génère des prédictions de prix basées sur moyenne mobile.
    """
    # 1. Lecture rawticker
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("subscribe", "rawticker") \
        .load()
    
    # 2. Parsing
    from spark_jobs.schemas import TICKER_SCHEMA
    
    ticker_df = kafka_df \
        .select(from_json(col("value").cast("string"), TICKER_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", current_timestamp())
    
    # 3. Extraction du symbole crypto depuis la paire
    # "XBT/USD" → "XBT"
    ticker_with_symbol = ticker_df \
        .withColumn("crypto_symbol", split(col("pair"), "/")[0])
    
    # 4. Watermark
    watermarked_df = ticker_with_symbol \
        .withWatermark("timestamp", "2 minutes")
    
    # 5. Window avec slide (sliding window)
    # Window de 3 minutes qui glisse toutes les 30 secondes
    windowed_df = watermarked_df \
        .groupBy(
            window(col("timestamp"), "3 minutes", "30 seconds"),
            col("crypto_symbol"),
            col("pair")
        ) \
        .agg(
            avg("last").alias("avg_price"),
            stddev("last").alias("price_volatility"),
            spark_min("last").alias("min_price"),
            spark_max("last").alias("max_price")
        )
    
    # 6. Calcul des prédictions
    prediction_df = windowed_df.select(
        col("window.end").alias("timestamp"),
        col("crypto_symbol"),
        col("avg_price").alias("predicted_price"),
        col("avg_price").alias("actual_price"),  # Sera mis à jour
        expr("'moving_average'").alias("model_name"),
        # Intervalle de confiance basé sur la volatilité
        (col("avg_price") - col("price_volatility")).alias("confidence_interval_low"),
        (col("avg_price") + col("price_volatility")).alias("confidence_interval_high")
    )
    
    # 7. Écriture
    query = write_to_timescale(
        prediction_df,
        "prediction_data",
        "/tmp/spark_checkpoints_prediction/prediction"
    )
    
    return query
```

## Concepts Spark Streaming

### Watermarking

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WATERMARK EXPLAINED                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Event Time:    T1────T2────T3────T4────T5────T6────T7────T8           │
│                   │     │     │     │     │     │     │     │            │
│  Watermark:     └─────┴─────┴─────┴─────┴─────┴─────┴─────┘            │
│                    <────── 2 minutes delay ──────>                      │
│                                                                         │
│  À T=15:00:00, le watermark est à 14:58:00                            │
│  → Données arrivant avant 14:58:00 sont ignorées                      │
│  → Permet de gérer le retard sans attendre indéfiniment                │
│                                                                         │
│  Code: .withWatermark("timestamp", "2 minutes")                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Windowing

| Type | Description | Usage |
|------|-------------|-------|
| **Tumbling** | Fenêtres disjointes de taille fixe | Agrégation par batch |
| **Sliding** | Fenêtres avec chevauchement | Calculs continus |
| **Session** | Fenêtres basées sur l'activité | Sessions utilisateur |

```python
# Tumbling window (non-chevauchant)
.groupBy(window(col("timestamp"), "3 minutes"))
# [12:00-12:03], [12:03-12:06], [12:06-12:09]...

# Sliding window (chevauchant)
.groupBy(window(col("timestamp"), "3 minutes", "30 seconds"))
# [12:00-12:03], [12:00:30-12:03:30], [12:01:00-12:04:00]...
```

### Checkpoints

```python
# Configuration checkpoint
.writeStream \
    .option("checkpointLocation", "/tmp/spark_checkpoints/article")

# Structure du checkpoint:
# /tmp/spark_checkpoints/
#   ├── article/
#   │   ├── offsets/          # Offsets Kafka par batch
#   │   ├── commits/          # Batches commités
#   │   ├── metadata          # Métadonnées
#   │   └── sources/          # État des sources
#   ├── ticker/
#   ├── trade/
#   ├── alert/
#   ├── sentiment/
#   └── prediction/
```

### Gestion des erreurs

```python
# Option: ignorer perte de données (partition non disponible)
.option("failOnDataLoss", "false")

# Try-except dans write_batch
def write_batch(batch_df, batch_id):
    try:
        if batch_df.count() > 0:
            batch_df.write.jdbc(...)
    except Exception as e:
        print(f"Erreur batch {batch_id}: {e}")
        # Log l'erreur, ne pas bloquer le stream
```

## Schémas de données

### ARTICLE_SCHEMA

```python
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    ArrayType, MapType
)

ARTICLE_SCHEMA = StructType([
    StructField("id", StringType(), False),
    StructField("title", StringType(), False),
    StructField("url", StringType(), False),
    StructField("website", StringType(), False),
    StructField("content", MapType(StringType(), StringType()), True),
    StructField("cryptocurrencies_mentioned", ArrayType(StringType()), True),
    StructField("sentiment", StructType([
        StructField("score", DoubleType(), True),
        StructField("label", StringType(), True),
    ]), True),
])
```

### TICKER_SCHEMA

```python
TICKER_SCHEMA = StructType([
    StructField("pair", StringType(), False),
    StructField("last", DoubleType(), False),
    StructField("bid", DoubleType(), True),
    StructField("ask", DoubleType(), True),
    StructField("volume_24h", DoubleType(), True),
    StructField("timestamp", DoubleType(), False),
    StructField("pct_change", DoubleType(), True),
])
```

## Commandes et Monitoring

### Démarrage des jobs

```bash
# Job d'ingestion
cd spark_jobs
source venv/bin/activate
nohup python kafka_to_timescale.py > ../logs/spark_ingestion.log 2>&1 &

# Job d'analyse
nohup python sentiment_prediction_job.py > ../logs/spark_analytics.log 2>&1 &
```

### Vérification des jobs

```bash
# Processus Spark
ps aux | grep -E "python.*spark|python.*sentiment" | grep -v grep

# Logs en temps réel
tail -f logs/spark_ingestion.log
tail -f logs/spark_analytics.log

# UI Spark (si disponible)
open http://localhost:4040  # UI du premier job
open http://localhost:4041  # UI du second job
```

### Nettoyage des checkpoints

```bash
# Arrêter les jobs
tail -f logs/spark_ingestion.log

# Nettoyer checkpoints
rm -rf /tmp/spark_checkpoints/*
rm -rf /tmp/spark_checkpoints_sentiment/*
rm -rf /tmp/spark_checkpoints_prediction/*

# Redémarrer les jobs
```

---

**Suite** : [05-timescaledb.md](./05-timescaledb.md) pour le stockage des données.
