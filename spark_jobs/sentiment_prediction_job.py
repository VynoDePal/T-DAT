"""
Job Spark pour analyse de sentiment et prédictions.
Consomme les données brutes et génère des analyses avancées.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, to_timestamp, current_timestamp,
    window, avg, stddev, min as spark_min, max as spark_max,
    lag, lead, expr, udf, explode
)
from pyspark.sql.types import DoubleType, StringType, StructType, StructField
from pyspark.sql.window import Window

import config
import schemas


def create_spark_session():
    """Crée et configure la session Spark avec ML."""
    import os
    import glob
    
    # Chercher les JARs dans le dossier local
    jars_dir = os.path.join(os.path.dirname(__file__), "jars")
    
    if os.path.exists(jars_dir):
        # Utiliser les JARs locaux
        jar_files = glob.glob(os.path.join(jars_dir, "*.jar"))
        jars_path = ",".join(jar_files)
        
        return SparkSession.builder \
            .appName(f"{config.SPARK_APP_NAME}_Analytics") \
            .master(config.SPARK_MASTER) \
            .config("spark.jars", jars_path) \
            .config("spark.sql.streaming.checkpointLocation", config.CHECKPOINT_LOCATION) \
            .getOrCreate()
    else:
        # Fallback: télécharger depuis Maven (ancienne méthode)
        print("⚠️  Dossier jars/ non trouvé. Téléchargement depuis Maven...")
        print(f"   Exécutez: ./scripts/download_spark_jars.sh")
        return SparkSession.builder \
            .appName(f"{config.SPARK_APP_NAME}_Analytics") \
            .master(config.SPARK_MASTER) \
            .config("spark.jars.packages", 
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                    "org.postgresql:postgresql:42.7.1") \
            .config("spark.sql.streaming.checkpointLocation", config.CHECKPOINT_LOCATION) \
            .getOrCreate()


def read_kafka_stream(spark, topic):
    """Lit un stream depuis Kafka."""
    return spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", topic) \
        .option("startingOffsets", "earliest") \
        .load()


def write_to_timescale(df, table_name, checkpoint_path):
    """Écrit un DataFrame dans TimescaleDB."""
    def write_batch(batch_df, batch_id):
        count = batch_df.count()
        if count > 0:
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
        .outputMode("append") \
        .option("checkpointLocation", checkpoint_path) \
        .start()


def process_sentiment_from_articles(spark):
    """
    Traite les articles pour extraire et stocker le sentiment.
    Crée des données agrégées de sentiment par crypto.
    """
    print("Démarrage de l'analyse de sentiment...")
    
    kafka_df = read_kafka_stream(spark, config.KAFKA_TOPICS['ARTICLE'])
    
    # Parser et extraire le sentiment
    article_df = kafka_df \
        .select(from_json(col("value").cast("string"), schemas.ARTICLE_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", current_timestamp())
    
    # Exploser les cryptos mentionnées pour avoir une ligne par crypto
    sentiment_df = article_df \
        .select(
            col("timestamp"),
            explode(col("cryptocurrencies_mentioned")).alias("crypto_symbol"),
            col("sentiment.score").alias("sentiment_score"),
            col("sentiment.label").alias("sentiment_label"),
            col("website").alias("source")
        ) \
        .withColumn("confidence", col("sentiment_score").cast(DoubleType()))
    
    # Ajouter une fenêtre temporelle pour agréger
    windowed_sentiment = sentiment_df \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(
            window(col("timestamp"), "5 minutes"),
            col("crypto_symbol")
        ) \
        .agg(
            avg("sentiment_score").alias("avg_sentiment_score"),
            avg("confidence").alias("avg_confidence")
        ) \
        .select(
            col("window.end").alias("timestamp"),
            col("crypto_symbol"),
            col("avg_sentiment_score").alias("sentiment_score"),
            expr("CASE WHEN avg_sentiment_score > 0.6 THEN 'positive' " +
                 "WHEN avg_sentiment_score < 0.4 THEN 'negative' " +
                 "ELSE 'neutral' END").alias("sentiment_label"),
            expr("'aggregated_articles'").alias("source"),
            col("avg_confidence").alias("confidence")
        )
    
    # Utiliser un checkpoint séparé pour sentiment
    query = write_to_timescale(
        windowed_sentiment,
        "sentiment_data",
        f"/tmp/spark_checkpoints_sentiment/sentiment"
    )
    
    return query


def process_price_predictions(spark):
    """
    Génère des prédictions de prix simples basées sur les tendances.
    Utilise les données de ticker pour prédire les prix futurs.
    """
    print("Démarrage des prédictions de prix...")
    
    kafka_df = read_kafka_stream(spark, config.KAFKA_TOPICS['TICKER'])
    
    # Parser les données de ticker
    ticker_df = kafka_df \
        .select(from_json(col("value").cast("string"), schemas.TICKER_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", to_timestamp(col("timestamp") / 1000))
    
    # Extraire le symbole de la crypto depuis la paire (ex: BTC/USD -> BTC)
    ticker_with_crypto = ticker_df \
        .withColumn("crypto_symbol", expr("split(pair, '/')[0]"))
    
    # Créer une fenêtre glissante pour calculer les tendances
    windowed_ticker = ticker_with_crypto \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(
            window(col("timestamp"), "5 minutes", "1 minute"),
            col("crypto_symbol"),
            col("pair")
        ) \
        .agg(
            avg("last").alias("avg_price"),
            stddev("last").alias("price_volatility"),
            spark_min("last").alias("min_price"),
            spark_max("last").alias("max_price")
        )
    
    # Prédiction simple: moyenne mobile + tendance
    # (Dans un cas réel, on utiliserait un modèle ML entraîné)
    prediction_df = windowed_ticker \
        .select(
            col("window.end").alias("timestamp"),
            col("crypto_symbol"),
            col("avg_price").alias("predicted_price"),
            col("avg_price").alias("actual_price"),  # Sera mis à jour plus tard
            expr("'moving_average'").alias("model_name"),
            (col("avg_price") - col("price_volatility")).alias("confidence_interval_low"),
            (col("avg_price") + col("price_volatility")).alias("confidence_interval_high")
        )
    
    query = write_to_timescale(
        prediction_df,
        "prediction_data",
        f"/tmp/spark_checkpoints_prediction/prediction"
    )
    
    return query


def main():
    """Point d'entrée principal du job d'analyse."""
    print("=" * 80)
    print("CRYPTO VIZ - Spark Analytics Job")
    print("Analyse de sentiment et prédictions de prix")
    print("=" * 80)
    
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    print(f"\nConfiguration:")
    print(f"  Kafka Servers: {config.KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  TimescaleDB: {config.TIMESCALE_JDBC_URL}")
    print(f"  Checkpoint Location: {config.CHECKPOINT_LOCATION}")
    print()
    
    queries = []
    
    try:
        # Démarrer l'analyse de sentiment
        queries.append(process_sentiment_from_articles(spark))
        
        # Démarrer les prédictions de prix
        queries.append(process_price_predictions(spark))
        
        print("\n" + "=" * 80)
        print("Tous les pipelines d'analyse sont actifs!")
        print("=" * 80)
        
        # Attendre la terminaison
        for query in queries:
            query.awaitTermination()
            
    except KeyboardInterrupt:
        print("\n\nArrêt demandé par l'utilisateur...")
    except Exception as e:
        print(f"\n\nErreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nArrêt des streams...")
        for query in queries:
            if query.isActive:
                query.stop()
        spark.stop()
        print("Job Spark terminé.")


if __name__ == "__main__":
    main()
