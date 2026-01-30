# Quick Start - Monitoring & Optimisations

Guide de démarrage rapide pour la nouvelle stack de monitoring.

---

## ⚡ Démarrage en 3 Minutes

### **1. Télécharger JMX Exporter (déjà fait)**

```bash
cd monitoring/jmx-exporter
# Le fichier jmx_prometheus_javaagent.jar est déjà présent
ls -lh jmx_prometheus_javaagent.jar
```

### **2. Démarrer tout le système**

```bash
cd /home/kevyn-odjo/Documents/T-DAT

# Arrêter l'ancien système si nécessaire
./scripts/stop_all.sh
./data_producers/stop_producers.sh

# Nettoyer les anciens topics (optionnel)
docker compose down -v

# Démarrer avec les nouvelles optimisations
./scripts/start_all.sh

# Attendre que tout soit UP (~60 secondes)

# Démarrer les producteurs optimisés
./data_producers/start_producers.sh

# Démarrer le health check monitor
./monitoring/start_monitoring.sh
```

### **3. Vérifier que tout fonctionne**

```bash
# Vérifier les containers Docker
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Devrait afficher:
# - crypto_viz_kafka (avec port 7071)
# - crypto_viz_zookeeper (avec port 7072)
# - crypto_viz_prometheus
# - crypto_viz_grafana
# - crypto_viz_kafka_exporter
# - crypto_viz_node_exporter
# - crypto_viz_redis_exporter
# - crypto_viz_postgres_exporter
# - crypto_viz_timescaledb
# - crypto_viz_redis
# - crypto_viz_backend
```

---

## Accès aux Interfaces

### **Grafana**
- URL: http://localhost:3000
- Login: `admin`
- Password: `admin`

**Première connexion**:
1. Aller sur http://localhost:3000
2. Login avec admin/admin
3. (Optionnel) Changer le mot de passe
4. Aller dans "Dashboards" → "Import"
5. Importer ces dashboards recommandés:
   - **11962**: Kafka Overview
   - **1860**: Node Exporter Full
   - **11835**: Redis Dashboard
   - **9628**: PostgreSQL Database

### **Prometheus**
- URL: http://localhost:9090
- Status/Targets: http://localhost:9090/targets
- Alerts: http://localhost:9090/alerts

**Vérifier les targets** (doivent être UP):
- kafka-broker
- zookeeper
- kafka-exporter
- node-exporter
- redis-exporter
- postgres-exporter
- prometheus

### **Django API**
- URL: http://localhost:8000/api/v1/
- Health check: http://localhost:8000/api/v1/health/

### **Health Check Metrics**
- URL: http://localhost:9999/metrics
- Format: Prometheus metrics

---

## Premiers Checks

### **1. Vérifier Kafka**

```bash
# Topics créés avec optimisations
docker exec crypto_viz_kafka kafka-topics \
  --bootstrap-server kafka:29092 \
  --list

# Devrait afficher:
# rawalert
# rawarticle
# rawticker
# rawtrade

# Voir la configuration d'un topic
docker exec crypto_viz_kafka kafka-topics \
  --bootstrap-server kafka:29092 \
  --describe --topic rawticker
```

**Attendu**: 6 partitions, compression LZ4, rétention 7 jours

### **2. Vérifier les Producteurs**

```bash
# Kraken producer logs
tail -20 logs/kraken_producer.log

# Devrait afficher des messages comme:
#  XBT/USD | Last: $89,800.10 | Change: 0.0% | Vol: 2,229.43
#  ETH/USD | $3,004.41 | Vol: 0.1963

# Article scraper logs
tail -20 logs/article_scraper.log

# Health check logs
tail -20 logs/health_check.log
```

### **3. Vérifier les Données dans TimescaleDB**

```bash
docker exec crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts \
  -c "SELECT COUNT(*) FROM ticker_data;"

docker exec crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts \
  -c "SELECT COUNT(*) FROM trade_data;"
```

**Attendu**: Nombres croissants de lignes

### **4. Tester le Cache Redis**

```bash
# Se connecter à Redis
docker exec -it crypto_viz_redis redis-cli

# Dans redis-cli:
# > KEYS crypto_viz:*
# > INFO stats
# > exit
```

---

## Grafana: Créer votre Premier Dashboard

### **Dashboard Crypto Viz Custom**

1. Dans Grafana, cliquer "+" → "Dashboard"
2. "Add visualization"
3. Choisir "Prometheus" comme data source
4. Ajouter ces panels:

#### **Panel 1: Messages Kafka par seconde**
```promql
rate(kafka_server_brokertopicmetrics_messagesinpersec_total[1m])
```

#### **Panel 2: Producteurs Status**
```promql
crypto_viz_producer_up
```

#### **Panel 3: Consumer Lag**
```promql
kafka_consumergroup_lag
```

#### **Panel 4: Cache Hit Rate**
```promql
rate(redis_keyspace_hits_total[5m]) / 
(rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) * 100
```

5. Sauvegarder le dashboard

---

## Alertes Configurées

Les alertes suivantes sont actives (voir `monitoring/prometheus/alerts/kafka-alerts.yml`):

### **Critiques** 🔴
- Kafka broker down (> 1 min)
- Kafka offline partitions (> 0)
- Kraken producer down (> 2 min)
- TimescaleDB down (> 1 min)

### **Warnings**
- Under-replicated partitions (> 5 min)
- High consumer lag (> 10k, 10 min)
- High ISR shrink rate
- Article scraper down (> 5 min)
- High disk usage (> 90%)
- High memory usage (> 90%)
- High CPU usage (> 80%, 10 min)

**Voir les alertes actives**:
http://localhost:9090/alerts

---

## Métriques à Surveiller

### **Santé Générale**

```promql
# Tous les services UP
up == 1

# Producteurs actifs
crypto_viz_producer_up == 1

# Health checks réussis
rate(crypto_viz_health_checks_total[5m])
```

### **Performance Kafka**

```promql
# Throughput (messages/sec)
rate(kafka_server_brokertopicmetrics_messagesinpersec_total[1m])

# Latence réseau
kafka_network_request_total_time_ms

# Partitions sous-répliquées (doit être 0)
kafka_server_replicamanager_underreplicatedpartitions
```

### **Cache Redis**

```promql
# Hit rate (doit être > 70%)
rate(redis_keyspace_hits_total[5m]) / 
(rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) * 100

# Mémoire utilisée
redis_memory_used_bytes

# Clients connectés
redis_connected_clients
```

---

## Commandes Utiles

### **Restart Services**

```bash
# Redémarrer Spark
./scripts/restart_spark.sh

# Redémarrer producteurs
cd data_producers
./stop_producers.sh && ./start_producers.sh

# Redémarrer monitoring
pkill -f health_check.py
./monitoring/start_monitoring.sh

# Redémarrer tout Docker
docker compose restart
```

### **Logs**

```bash
# Suivre tous les logs
tail -f logs/*.log

# Logs Docker
docker logs crypto_viz_kafka --tail 100
docker logs crypto_viz_prometheus --tail 50

# Logs health check en temps réel
tail -f logs/health_check.log
```

### **Métriques en ligne de commande**

```bash
# Prometheus metrics en temps réel
watch -n 2 'curl -s http://localhost:9090/api/v1/query?query=up | jq'

# Health check metrics
curl -s http://localhost:9999/metrics | grep crypto_viz

# Redis stats
docker exec crypto_viz_redis redis-cli INFO stats
```
