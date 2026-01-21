# ⚠️ Configuration Kafka Requise

## Statut Actuel des Services

| Service | Statut | Détails |
|---------|--------|---------|
| **Django API** | ✅ OPÉRATIONNEL | Migrations appliquées, API fonctionnelle |
| **TimescaleDB** | ✅ OPÉRATIONNEL | Port 15432, prêt à recevoir des données |
| **Redis** | ✅ OPÉRATIONNEL | Port 6380 |
| **Spark Ingestion** | ❌ BLOQUÉ | Topics Kafka introuvables |
| **Spark Analytics** | ❌ BLOQUÉ | Dépend de Spark Ingestion |

---

## 🔴 Problème Principal : Topics Kafka Manquants

### Erreur Observée

```
org.apache.kafka.common.errors.UnknownTopicOrPartitionException: 
This server does not host this topic-partition.
```

### Cause

Les topics Kafka requis par l'application **n'existent pas** sur le serveur `20.199.136.163:9092`.

**Topics requis** :
- `rawticker` - Données de prix en temps réel
- `rawtrade` - Transactions/trades
- `rawarticle` - Articles de presse crypto
- `rawalert` - Alertes de marché

---

## ✅ Solutions

### Option 1 : Créer les Topics Kafka (RECOMMANDÉ)

Si vous avez accès au serveur Kafka :

```bash
# Se connecter au serveur Kafka
ssh user@20.199.136.163

# Créer les topics
kafka-topics.sh --create \
  --topic rawticker \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

kafka-topics.sh --create \
  --topic rawtrade \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

kafka-topics.sh --create \
  --topic rawarticle \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1

kafka-topics.sh --create \
  --topic rawalert \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

**Vérifier** :
```bash
kafka-topics.sh --list --bootstrap-server localhost:9092
```

---

### Option 2 : Demander à l'Administrateur

Si vous n'avez pas accès au serveur Kafka, contactez l'administrateur système et demandez :

> "Bonjour, j'ai besoin de 4 topics Kafka sur le serveur 20.199.136.163:9092 pour mon application :
> - rawticker
> - rawtrade
> - rawarticle
> - rawalert
> 
> Configuration suggérée : 3 partitions, replication-factor 1"

---

### Option 3 : Mode Développement Local

Pour développer sans serveur Kafka distant, installez Kafka localement :

```bash
# Ubuntu/Debian
sudo apt-get install kafka

# Ou avec Docker
docker run -d \
  --name kafka \
  -p 9092:9092 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  confluentinc/cp-kafka:latest
```

Puis modifiez `.env` :
```bash
KAFKA_SERVERS=localhost:9092
```

---

## 📋 Vérification

Après avoir créé les topics :

```bash
# Vérifier la connexion
./scripts/check_kafka_topics.sh

# Relancer les services
./scripts/stop_all.sh
./scripts/start_all.sh

# Vérifier les logs
tail -f logs/spark_ingestion.log
```

**Logs attendus** :
```
Démarrage du traitement du stream TICKER...
Démarrage du traitement du stream TRADE...
Démarrage du traitement du stream ARTICLE...
Démarrage du traitement du stream ALERT...
Tous les streams sont actifs!
```

---

## 🎯 Prochaines Étapes

**Une fois les topics créés** :

1. ✅ Les jobs Spark se connecteront automatiquement
2. ✅ Les données Kafka seront écrites dans TimescaleDB
3. ✅ L'API Django pourra servir les données historiques
4. ✅ Le système sera pleinement opérationnel

---

## 📞 Besoin d'Aide ?

**Vérifier l'état actuel** :
```bash
# Services Docker
docker compose ps

# Connexion Kafka
nc -zv 20.199.136.163 9092

# API Django
curl http://localhost:8000/api/v1/health/

# Logs
tail -f logs/*.log
```

**Diagnostic complet** :
```bash
./scripts/diagnostic.sh
```

---

**Date de création** : 28 novembre 2024  
**Dernière mise à jour** : 28 novembre 2024
