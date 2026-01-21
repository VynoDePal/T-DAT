#!/bin/bash

# Script pour télécharger les JARs Spark nécessaires

set -e

echo "========================================="
echo "Téléchargement des JARs Spark"
echo "========================================="
echo ""

# Créer le répertoire pour les JARs
JARS_DIR="../spark_jobs/jars"
mkdir -p $JARS_DIR

cd $JARS_DIR

echo "[INFO] Téléchargement des dépendances Spark..."

# Spark SQL Kafka
echo "  - spark-sql-kafka-0-10_2.12:3.5.0"
wget -q -O spark-sql-kafka-0-10_2.12-3.5.0.jar \
  https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar

# Kafka Clients
echo "  - kafka-clients:3.4.1"
wget -q -O kafka-clients-3.4.1.jar \
  https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar

# PostgreSQL JDBC Driver
echo "  - postgresql:42.7.1"
wget -q -O postgresql-42.7.1.jar \
  https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar

# Commons Pool2
echo "  - commons-pool2:2.11.1"
wget -q -O commons-pool2-2.11.1.jar \
  https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

# Spark Token Provider Kafka
echo "  - spark-token-provider-kafka-0-10_2.12:3.5.0"
wget -q -O spark-token-provider-kafka-0-10_2.12-3.5.0.jar \
  https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar

echo ""
echo "✓ Tous les JARs ont été téléchargés dans: $JARS_DIR"
echo ""
echo "Fichiers téléchargés:"
ls -lh *.jar
