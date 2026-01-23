"""
Job Spark Structured Streaming principal.
Consomme les 4 topics Kafka et écrit dans TimescaleDB.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, to_timestamp, current_timestamp, from_unixtime,
    expr, get_json_object, explode
)
from pyspark.sql.types import TimestampType

import config
import schemas


def create_spark_session():
    """Crée et configure la session Spark."""
    import os
    import glob
    
    # Chercher les JARs dans le dossier local
    jars_dir = os.path.join(os.path.dirname(__file__), "jars")
    
    if os.path.exists(jars_dir):
        # Utiliser les JARs locaux
        jar_files = glob.glob(os.path.join(jars_dir, "*.jar"))
        jars_path = ",".join(jar_files)
        
        return SparkSession.builder \
            .appName(config.SPARK_APP_NAME) \
            .master(config.SPARK_MASTER) \
            .config("spark.jars", jars_path) \
            .config("spark.sql.streaming.checkpointLocation", config.CHECKPOINT_LOCATION) \
            .getOrCreate()
    else:
        # Fallback: télécharger depuis Maven (ancienne méthode)
        print(f"    Dossier jars/ non trouvé. Téléchargement depuis Maven...")
        print(f"    Exécutez: ./scripts/download_spark_jars.sh")
        return SparkSession.builder \
            .appName(config.SPARK_APP_NAME) \
            .master(config.SPARK_MASTER) \
            .config("spark.jars.packages", 
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                    "org.postgresql:postgresql:42.7.1") \
            .config("spark.sql.streaming.checkpointLocation", config.CHECKPOINT_LOCATION) \
            .getOrCreate()


def read_kafka_stream(spark, topic):
    """
    Lit un stream depuis Kafka.
    
    Args:
        spark: SparkSession
        topic: Nom du topic Kafka
        
    Returns:
        DataFrame Kafka
    """
    return spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()


def write_to_timescale(df, table_name, checkpoint_path):
    """
    Écrit un DataFrame dans TimescaleDB via JDBC.
    
    Args:
        df: DataFrame Spark
        table_name: Nom de la table TimescaleDB
        checkpoint_path: Chemin pour les checkpoints
    """
    def write_batch(batch_df, batch_id):
        """Fonction pour écrire chaque batch."""
        if batch_df.count() > 0:
            batch_df.write \
                .format("jdbc") \
                .option("url", config.TIMESCALE_JDBC_URL) \
                .option("dbtable", table_name) \
                .option("user", config.TIMESCALE_CONFIG['user']) \
                .option("password", config.TIMESCALE_CONFIG['password']) \
                .option("driver", "org.postgresql.Driver") \
                .mode("append") \
                .save()
            print(f"Batch {batch_id}: {batch_df.count()} rows écrites dans {table_name}")
    
    return df.writeStream \
        .foreachBatch(write_batch) \
        .option("checkpointLocation", checkpoint_path) \
        .start()


def process_ticker_stream(spark):
    """
    Traite le stream rawticker.
    Transforme et écrit dans ticker_data.
    """
    print("Démarrage du traitement du stream TICKER...")
    
    # Lire le stream Kafka
    kafka_df = read_kafka_stream(spark, config.KAFKA_TOPICS['TICKER'])
    
    # Parser le JSON et transformer
    ticker_df = kafka_df \
        .select(from_json(col("value").cast("string"), schemas.TICKER_SCHEMA).alias("data")) \
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
    
    # Écrire dans TimescaleDB
    query = write_to_timescale(
        ticker_df, 
        "ticker_data",
        f"{config.CHECKPOINT_LOCATION}/ticker"
    )
    
    return query


def process_trade_stream(spark):
    """
    Traite le stream rawtrade.
    Transforme et écrit dans trade_data.
    """
    print("Démarrage du traitement du stream TRADE...")
    
    kafka_df = read_kafka_stream(spark, config.KAFKA_TOPICS['TRADE'])
    
    trade_df = kafka_df \
        .select(from_json(col("value").cast("string"), schemas.TRADE_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", from_unixtime(col("timestamp")).cast(TimestampType())) \
        .select(
            col("timestamp"),
            col("pair"),
            col("price"),
            col("volume"),
            col("side")
        )
    
    query = write_to_timescale(
        trade_df,
        "trade_data",
        f"{config.CHECKPOINT_LOCATION}/trade"
    )
    
    return query


def process_article_stream(spark):
    """
    Traite le stream rawarticle.
    Extrait le sentiment et écrit dans article_data.
    """
    print("Démarrage du traitement du stream ARTICLE...")
    
    kafka_df = read_kafka_stream(spark, config.KAFKA_TOPICS['ARTICLE'])
    
    article_df = kafka_df \
        .select(from_json(col("value").cast("string"), schemas.ARTICLE_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", current_timestamp()) \
        .withColumn("summary", col("content.summary")) \
        .select(
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
    
    query = write_to_timescale(
        article_df,
        "article_data",
        f"{config.CHECKPOINT_LOCATION}/article"
    )
    
    return query


def process_alert_stream(spark):
    """
    Traite le stream rawalert.
    Transforme et écrit dans alert_data.
    """
    print("Démarrage du traitement du stream ALERT...")
    
    kafka_df = read_kafka_stream(spark, config.KAFKA_TOPICS['ALERT'])
    
    alert_df = kafka_df \
        .select(from_json(col("value").cast("string"), schemas.ALERT_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("timestamp", to_timestamp(col("timestamp") / 1000)) \
        .withColumn("alert_type", 
                   expr("CASE WHEN change > 0 THEN 'PRICE_UP' ELSE 'PRICE_DOWN' END")) \
        .select(
            col("timestamp"),
            col("pair"),
            col("last").alias("last_price"),
            col("change").alias("change_percent"),
            col("threshold"),
            col("alert_type")
        )
    
    query = write_to_timescale(
        alert_df,
        "alert_data",
        f"{config.CHECKPOINT_LOCATION}/alert"
    )
    
    return query


def main():
    """Point d'entrée principal du job Spark."""
    print("=" * 80)
    print("CRYPTO VIZ - Spark Streaming Job")
    print("Consommation des topics Kafka et écriture dans TimescaleDB")
    print("=" * 80)
    
    # Créer la session Spark
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    print(f"\nConfiguration:")
    print(f"  Kafka Servers: {config.KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  TimescaleDB: {config.TIMESCALE_JDBC_URL}")
    print(f"  Checkpoint Location: {config.CHECKPOINT_LOCATION}")
    print()
    
    # Démarrer les streams pour chaque topic
    queries = []
    
    try:
        queries.append(process_ticker_stream(spark))
        queries.append(process_trade_stream(spark))
        queries.append(process_article_stream(spark))
        queries.append(process_alert_stream(spark))
        
        print("\n" + "=" * 80)
        print("Tous les streams sont actifs!")
        print("=" * 80)
        
        # Attendre que tous les streams se terminent
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
