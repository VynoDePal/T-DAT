#!/bin/bash

# Script pour vérifier les topics Kafka disponibles

KAFKA_SERVER="20.199.136.163:9092"

echo "========================================="
echo "Vérification Kafka Topics"
echo "========================================="
echo ""
echo "Serveur Kafka: $KAFKA_SERVER"
echo ""

# Vérifier la connexion
echo "[1] Test de connexion..."
if timeout 3 nc -zv $KAFKA_SERVER 2>&1 | grep -q succeeded; then
    echo "✓ Connexion réussie à $KAFKA_SERVER"
else
    echo "✗ Impossible de se connecter à $KAFKA_SERVER"
    exit 1
fi

echo ""
echo "[2] Topics requis par l'application:"
echo "  - rawticker"
echo "  - rawtrade"
echo "  - rawarticle"
echo "  - rawalert"
echo ""

echo "[3] Information importante:"
echo ""
echo "⚠️  Les topics Kafka doivent exister sur le serveur avant de lancer Spark."
echo ""
echo "Si vous avez accès au serveur Kafka, créez les topics avec:"
echo ""
echo "  kafka-topics.sh --create --topic rawticker --bootstrap-server $KAFKA_SERVER"
echo "  kafka-topics.sh --create --topic rawtrade --bootstrap-server $KAFKA_SERVER"
echo "  kafka-topics.sh --create --topic rawarticle --bootstrap-server $KAFKA_SERVER"
echo "  kafka-topics.sh --create --topic rawalert --bootstrap-server $KAFKA_SERVER"
echo ""
echo "Ou demandez à l'administrateur du serveur Kafka de créer ces topics."
echo ""
echo "========================================="
echo "Note: Les jobs Spark échoueront tant que ces topics n'existent pas."
echo "========================================="
