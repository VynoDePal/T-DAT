# Monitoring et Observabilité

## Vue d'ensemble

Le monitoring de CRYPTO VIZ repose sur **Prometheus** pour la collecte des métriques et **Grafana** pour la visualisation. Plusieurs exporters collectent les métriques des différents services.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MONITORING STACK CRYPTO VIZ                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌───────────────────────────────────────────────────────────────────┐ │
│   │                        PROMETHEUS (9090)                          │ │
│   │                                                                   │ │
│   │  • Collecte toutes les 15s                                        │ │
│   │  • Stockage 15 jours (configurable)                               │ │
│   │  • Alerting rules (optionnel)                                     │ │
│   │                                                                   │ │
│   └───────────────────────────────────────────────────────────────────┘ │
│                                │                                        │
│           ┌────────────────────┼────────────────────┐                   │
│           ▼                    ▼                    ▼                   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│   │  EXPORTERS   │  │  EXPORTERS   │  │  EXPORTERS   │                  │
│   ├──────────────┤  ├──────────────┤  ├──────────────┤                  │
│   │Node Exporter │  │Kafka Exporter│  │Postgres      │                  │
│   │(9100)        │  │(9308)        │  │Exporter(9187)│                  │
│   ├──────────────┤  ├──────────────┤  ├──────────────┤                  │
│   │• CPU         │  │• Topics      │  │• Queries     │                  │
│   │• RAM         │  │• Partitions  │  │• Connections │                  │
│   │• Disk        │  │• Consumer lag│  │• Locks       │                  │
│   │• Network     │  │• Throughput  │  │• Transactions│                  │
│   └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
│   ┌──────────────┐  ┌──────────────┐                                    │
│   │Redis Exporter│  │Docker Metrics│                                    │
│   │(9121)        │  │(cAdvisor)    │                                    │
│   ├──────────────┤  ├──────────────┤                                    │
│   │• Memory      │  │• CPU per     │                                    │
│   │• Ops/sec     │  │  container   │                                    │
│   │• Hits/misses │  │• Memory      │                                    │
│   └──────────────┘  └──────────────┘                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         GRAFANA (3000)                                    │
│                                                                           │
│   ┌───────────────────────────────────────────────────────────────────┐   │
│   │                      DASHBOARDS                                   │   │
│   │                                                                   │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│   │  │ System      │  │ Kafka       │  │ PostgreSQL  │                │   │
│   │  │ Overview    │  │ Overview    │  │ Overview    │                │   │
│   │  ├─────────────┤  ├─────────────┤  ├─────────────┤                │   │
│   │  │• CPU %      │  │• Messages   │  │• QPS        │                │   │
│   │  │• RAM %      │  │  /sec       │  │• Active     │                │   │
│   │  │• Disk I/O   │  │• Lag        │  │  connections│                │   │
│   │  │• Network    │  │• Partitions │  │• Cache hits │                │   │
│   │  └─────────────┘  └─────────────┘  └─────────────┘                │   │
│   │                                                                   │   │
│   │  ┌─────────────┐  ┌─────────────┐                                 │   │
│   │  │ Redis       │  │ CRYPTO VIZ  │                                 │   │
│   │  │ Overview    │  │ Custom      │                                 │   │
│   │  ├─────────────┤  ├─────────────┤                                 │   │
│   │  │• Memory     │  │• Articles   │                                 │   │
│   │  │• Commands   │  │  /heure     │                                 │   │
│   │  │• Hit rate   │  │• Prix temps │                                 │   │
│   │  └─────────────┘  │  réel       │                                 │   │
│   │                   │• Sentiment  │                                 │   │
│   │                   └─────────────┘                                 │   │
│   │                                                                   │   │
│   └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Architecture de monitoring

### Prometheus

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s      # Collecte toutes les 15s
  evaluation_interval: 15s  # Évaluation règles toutes les 15s
  external_labels:
    cluster: 'crypto-viz'
    replica: '{{.ExternalURL}}'

alerting:
  alertmanagers: []  # Pas d'alertmanager configuré par défaut

rule_files: []  # Pas de règles d'alerting par défaut

scrape_configs:
  # Prometheus lui-même
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter - Métriques système
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # Kafka Exporter - Métriques Kafka
  - job_name: 'kafka-exporter'
    static_configs:
      - targets: ['kafka-exporter:9308']

  # PostgreSQL Exporter - Métriques TimescaleDB
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis Exporter - Métriques Redis
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Django - Métriques applicatives (si exposées)
  - job_name: 'django'
    static_configs:
      - targets: ['django:8000']
    metrics_path: '/metrics'  # Nécessite django-prometheus
```

### Exporters

#### 1. Node Exporter (Système)

```yaml
# docker-compose.yml
node-exporter:
  image: prom/node-exporter:v1.8.2
  ports:
    - "9100:9100"
  volumes:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    - /:/rootfs:ro
  command:
    - '--path.procfs=/host/proc'
    - '--path.sysfs=/host/sys'
    - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
```

**Métriques collectées**:
- `node_cpu_seconds_total` - Usage CPU par mode
- `node_memory_MemAvailable_bytes` - Mémoire disponible
- `node_disk_io_time_seconds_total` - I/O disque
- `node_network_receive_bytes_total` - Réseau entrant
- `node_filesystem_avail_bytes` - Espace disque disponible

#### 2. Kafka Exporter

```yaml
kafka-exporter:
  image: danielqsj/kafka-exporter:v1.8.0
  ports:
    - "9308:9308"
  command:
    - '--kafka.server=kafka:29092'
```

**Métriques collectées**:
- `kafka_topic_partition_current_offset` - Offset actuel par partition
- `kafka_consumergroup_lag` - Lag des consommateurs
- `kafka_topic_partition_in_sync_replica` - Réplicas en sync
- `kafka_broker_messages_in_total` - Messages entrants par broker

#### 3. PostgreSQL Exporter

```yaml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter:v0.16.0
  ports:
    - "9187:9187"
  environment:
    - DATA_SOURCE_NAME=postgresql://postgres:password@timescaledb:5432/crypto_viz_ts?sslmode=disable
```

**Métriques collectées**:
- `pg_stat_database_xact_commit` - Transactions commitées
- `pg_stat_database_numbackends` - Connexions actives
- `pg_stat_user_tables_n_tup_ins` - Insertions par table
- `pg_stat_user_tables_n_tup_upd` - Updates par table

#### 4. Redis Exporter

```yaml
redis-exporter:
  image: oliver006/redis_exporter:v1.67.0
  ports:
    - "9121:9121"
  environment:
    - REDIS_ADDR=redis:6379
```

**Métriques collectées**:
- `redis_memory_used_bytes` - Mémoire utilisée
- `redis_commands_processed_total` - Commandes traitées
- `redis_keyspace_hits_total` - Cache hits
- `redis_keyspace_misses_total` - Cache misses

## Grafana

### Configuration

```yaml
# docker-compose.yml
grafana:
  image: grafana/grafana:11.3.0
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_USER=admin
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_USERS_ALLOW_SIGN_UP=false
  volumes:
    - grafana_data:/var/lib/grafana
    - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

### Provisioning automatique

```yaml
# monitoring/grafana/provisioning/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

# monitoring/grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

### Dashboards disponibles

| Dashboard | ID | Description |
|-----------|-----|-------------|
| **Node Exporter Full** | 1860 | Métriques système complètes |
| **Kafka Exporter** | 7589 | Topics, partitions, consumer lag |
| **PostgreSQL Database** | 9628 | Queries, connections, locks |
| **Redis Dashboard** | 763 | Memory, operations, performance |
| **Docker and System Monitoring** | 893 | Conteneurs Docker |

## Métriques clés à surveiller

### 1. Système (Node Exporter)

```promql
# CPU Usage
100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory Usage
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))

# Disk Usage
100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)

# Network I/O
rate(node_network_receive_bytes_total[5m])
rate(node_network_transmit_bytes_total[5m])
```

### 2. Kafka

```promql
# Messages par seconde
rate(kafka_topic_partition_current_offset[1m])

# Consumer Lag (important!)
kafka_consumergroup_lag{topic="rawarticle"}
kafka_consumergroup_lag{topic="rawticker"}

# Taille des partitions
kafka_topic_partition_current_offset - kafka_topic_partition_oldest_offset
```

**Alertes recommandées**:
- Consumer lag > 1000 messages
- Partition size > 1GB
- Broker indisponible

### 3. PostgreSQL/TimescaleDB

```promql
# Connexions actives
pg_stat_database_numbackends{datname="crypto_viz_ts"}

# Transactions par seconde
rate(pg_stat_database_xact_commit{datname="crypto_viz_ts"}[1m])

# Temps de query (si activé)
pg_stat_statements_mean_time

# Tables les plus actives
topk(10, pg_stat_user_tables_n_tup_ins)
```

### 4. Application (Custom)

```python
# Ajouter dans Django (optionnel avec django-prometheus)
# crypto_viz_backend/api/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Compteurs
articles_scraped = Counter('crypto_articles_scraped_total', 'Total articles scrapés', ['source'])
tickers_received = Counter('crypto_tickers_received_total', 'Total tickers reçus', ['pair'])

# Histogrammes (latences)
scraping_duration = Histogram('crypto_scraping_duration_seconds', 'Temps de scraping')
api_request_duration = Histogram('crypto_api_request_duration_seconds', 'Temps requête API', ['endpoint'])

# Gauges (valeurs actuelles)
last_article_timestamp = Gauge('crypto_last_article_timestamp', 'Timestamp dernier article', ['source'])
current_price = Gauge('crypto_current_price', 'Prix actuel', ['pair'])
```

## Health Checks

### Commandes de vérification

```bash
#!/bin/bash
# health_check.sh

echo "=== Health Check CRYPTO VIZ ==="

# 1. Docker containers
echo "[1/6] Docker containers..."
docker-compose ps | grep -E "Up|running" | wc -l

# 2. Kafka
echo "[2/6] Kafka..."
curl -s http://localhost:9308/metrics | grep -c "kafka_topic_partition"

# 3. TimescaleDB
echo "[3/6] TimescaleDB..."
docker exec t-dat-timescaledb-1 pg_isready -U postgres > /dev/null && echo "OK" || echo "FAIL"

# 4. Django
echo "[4/6] Django API..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/sentiment/bitcoin/historique/

# 5. Prometheus
echo "[5/6] Prometheus..."
curl -s http://localhost:9090/api/v1/status/targets | grep -c '"health":"up"'

# 6. Grafana
echo "[6/6] Grafana..."
curl -s http://localhost:3000/api/health | grep -c "ok"

echo "=== Health Check terminé ==="
```

### Monitoring des jobs Python

```bash
# Vérifier processus actifs
echo "Jobs Python:"
ps aux | grep -E "article_scraper|kraken_producer|kafka_to_timescale|sentiment_prediction" | grep -v grep

echo ""
echo "Processus Spark (Java):"
ps aux | grep "org.apache.spark.deploy.SparkSubmit" | grep -v grep

echo ""
echo "Logs récents:"
tail -5 logs/article_scraper.log
tail -5 logs/kraken_producer.log
tail -5 logs/spark_ingestion.log
tail -5 logs/spark_analytics.log
```

## Alerting (Optionnel)

### Configuration AlertManager

```yaml
# monitoring/prometheus/alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@cryptoviz.com'

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@cryptoviz.com'
        subject: 'CRYPTO VIZ Alert: {{ .GroupLabels.alertname }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

### Règles d'alerte

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: crypto-viz
    rules:
      # Haute utilisation CPU
      - alert: HighCPUUsage
        expr: 100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"
      
      # Consumer lag Kafka
      - alert: KafkaConsumerLag
        expr: kafka_consumergroup_lag > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Kafka consumer lag high"
          description: "Consumer group has {{ $value }} messages lag"
      
      # Connexions DB élevées
      - alert: HighDBConnections
        expr: pg_stat_database_numbackends > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connections"
          description: "{{ $value }} active connections"
```

## Tableaux de bord recommandés

### Dashboard CRYPTO VIZ Custom

Créer un dashboard Grafana avec les panels:

```json
{
  "dashboard": {
    "title": "CRYPTO VIZ Overview",
    "panels": [
      {
        "title": "Articles Scraped (per hour)",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(crypto_articles_scraped_total[1h])",
            "legendFormat": "{{ source }}"
          }
        ]
      },
      {
        "title": "Tickers Received (per minute)",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(crypto_tickers_received_total[1m])",
            "legendFormat": "{{ pair }}"
          }
        ]
      },
      {
        "title": "Consumer Lag",
        "type": "graph",
        "targets": [
          {
            "expr": "kafka_consumergroup_lag",
            "legendFormat": "{{ topic }}"
          }
        ]
      },
      {
        "title": "Database Queries/sec",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(pg_stat_database_xact_commit[1m])",
            "legendFormat": "commits/sec"
          }
        ]
      }
    ]
  }
}
```

## URLs de monitoring

| Service | URL | Description |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | Interface exploration métriques |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |
| Node Exporter | http://localhost:9100/metrics | Métriques brutes système |
| Kafka Exporter | http://localhost:9308/metrics | Métriques brutes Kafka |
| PostgreSQL Exporter | http://localhost:9187/metrics | Métriques brutes DB |
| Redis Exporter | http://localhost:9121/metrics | Métriques brutes Redis |

## Commandes utiles

```bash
# Vérifier cibles Prometheus
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# Requête PromQL manuelle
curl "http://localhost:9090/api/v1/query?query=up"

# Redémarrer stack monitoring
docker-compose restart prometheus grafana

# Logs Grafana
docker-compose logs -f grafana

# Reset mot de passe Grafana
docker exec t-dat-grafana-1 grafana-cli admin reset-admin-password newpassword
```

---

**Fin de la documentation.**

Retour au [README principal](./README.md).
