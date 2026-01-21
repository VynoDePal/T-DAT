"""
Schémas de données pour les messages Kafka.
"""
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    LongType, ArrayType, MapType
)


# Schéma pour rawticker
TICKER_SCHEMA = StructType([
    StructField("pair", StringType(), False),
    StructField("last", DoubleType(), False),
    StructField("bid", DoubleType(), True),
    StructField("ask", DoubleType(), True),
    StructField("volume_24h", DoubleType(), True),
    StructField("timestamp", DoubleType(), False),
    StructField("pct_change", DoubleType(), True),
])

# Schéma pour rawtrade
TRADE_SCHEMA = StructType([
    StructField("pair", StringType(), False),
    StructField("price", DoubleType(), False),
    StructField("volume", DoubleType(), False),
    StructField("timestamp", DoubleType(), False),
    StructField("side", StringType(), False),  # 'b' for buy, 's' for sell
])

# Schéma pour rawarticle
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

# Schéma pour rawalert
ALERT_SCHEMA = StructType([
    StructField("pair", StringType(), False),
    StructField("last", DoubleType(), False),
    StructField("change", DoubleType(), False),
    StructField("threshold", DoubleType(), False),
    StructField("timestamp", LongType(), False),
])
