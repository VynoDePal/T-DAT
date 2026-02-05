# Apache Kafka - Configuration et Gestion

## Vue d'ensemble

Apache Kafka sert de **Message Broker** central dans l'architecture CRYPTO VIZ. Il assure la durabilité, la scalabilité et la distribution des données entre les producers et le traitement Spark.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         APACHE KAFKA 4.1.1                              │
│                    (Mode KRaft - Sans ZooKeeper)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐ │
│   │  PRODUCERS  │───▶│    KAFKA    │───▶│  CONSUMERS  │    │STORAGE  │ │
│   │             │    │             │    │             │    │         │ │
│   │• Scraper    │    │  ┌───────┐  │    │• Spark Job 1│    │• Logs   │ │
│   │• Kraken WS │    │  │ Topics │  │    │• Spark Job 2│    │• Metrics│ │
│   └─────────────┘    │  │• raw*  │  │    └─────────────┘    └─────────┘ │
│                      │  └───────┘  │                                     │
│                      │             │                                     │
│                      │  ┌───────┐  │                                     │
│                      │  │Broker │  │                                     │
│                      │  │Node 1 │  │                                     │
│                      │  └───────┘  │                                     │
│                      │             │                                     │
│                      │  ┌───────┐  │                                     │
│                      │  │KRaft  │  │                                     │
│                      │  │Quorum │  │                                     │
│                      │  └───────┘  │                                     │
│                      └─────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Configuration KRaft (sans ZooKeeper)

Kafka 4.x utilise le mode **KRaft** (Kafka Raft) qui élimine la dépendance à ZooKeeper.

### Configuration du nœud

```yaml
# docker-compose.yml - Service Kafka
services:
  kafka:
    image: apache/kafka:4.1.1
    ports:
      - "9092:9092"    # Client PLAINTEXT
      - "29092:29092"  # Internal PLAINTEXT
      - "9093:9093"    # Controller
    environment:
      # Identité du nœud
      KAFKA_NODE_ID: 1
      
      # Rôles du nœud (combined = broker + controller)
      KAFKA_PROCESS_ROLES: broker,controller
      
      # Listeners
      KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093,PLAINTEXT_INTERNAL://:29092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092,PLAINTEXT_INTERNAL://kafka:29092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT,PLAINTEXT_INTERNAL:PLAINTEXT
      
      # Communication interne
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT_INTERNAL
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      
      # Réplication (single-node)
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      
      # Performance
      KAFKA_NUM_PARTITIONS: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
```

### Explication des listeners

```
┌─────────────────────────────────────────────────────────────┐
│                     LISTENERS KAFKA                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   PLAINTEXT://:9092 (localhost:9092)                       │
│   ├── Usage: Clients externes (Spark, Producers locaux)   │
│   └── Accessible depuis: Host machine                       │
│                                                             │
│   PLAINTEXT_INTERNAL://:29092 (kafka:29092)              │
│   ├── Usage: Communication inter-broker                     │
│   └── Accessible depuis: Réseau Docker interne             │
│                                                             │
│   CONTROLLER://:9093                                        │
│   ├── Usage: KRaft consensus (quorum)                      │
│   └── Accessible depuis: Interne uniquement                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Topics

### Liste des topics

| Topic | Type | Producteur | Consommateur | Clé | Rétention |
|-------|------|------------|--------------|-----|-----------|
| `rawarticle` | Article crypto | article_scraper.py | Spark (2 jobs) | source | 7 jours |
| `rawticker` | Prix temps réel | kraken_producer.py | Spark (2 jobs) | pair | 7 jours |
| `rawtrade` | Transactions | kraken_producer.py | Spark (1 job) | pair | 7 jours |
| `rawalert` | Alertes prix | kraken_producer.py | Spark (1 job) | pair | 1 jour |

### Création manuelle des topics

```bash
# Se connecter au conteneur Kafka
docker exec -it t-dat-kafka-1 bash

# Créer un topic
cd /opt/kafka/bin
./kafka-topics.sh --bootstrap-server localhost:29092 \
  --create --topic rawarticle \
  --partitions 1 --replication-factor 1

# Lister les topics
./kafka-topics.sh --bootstrap-server localhost:29092 --list

# Détails d'un topic
./kafka-topics.sh --bootstrap-server localhost:29092 \
  --describe --topic rawarticle
```

### Configuration des topics

```bash
# rawarticle - Articles avec sentiment
./kafka-configs.sh --bootstrap-server localhost:29092 \
  --entity-type topics --entity-name rawarticle \
  --alter --add-config retention.ms=604800000,cleanup.policy=delete,compression.type=lz4

# rawticker - Prix temps réel (volume élevé)
./kafka-configs.sh --bootstrap-server localhost:29092 \
  --entity-type topics --entity-name rawticker \
  --alter --add-config retention.ms=604800000,segment.ms=3600000

# rawalert - Alertes (volume faible, rétention courte)
./kafka-configs.sh --bootstrap-server localhost:29092 \
  --entity-type topics --entity-name rawalert \
  --alter --add-config retention.ms=86400000
```

### Détail des configurations

| Config | rawarticle | rawticker | rawtrade | rawalert |
|--------|------------|-----------|----------|----------|
| `retention.ms` | 7 jours | 7 jours | 7 jours | 1 jour |
| `cleanup.policy` | delete | delete | delete | delete |
| `compression.type` | lz4 | lz4 | lz4 | lz4 |
| `segment.ms` | 24h | 1h | 1h | 24h |
| `min.insync.replicas` | 1 | 1 | 1 | 1 |

## Produire et Consommer

### Ligne de commande (debug)

```bash
# Produire un message
docker exec -it t-dat-kafka-1 /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:29092 \
  --topic rawarticle \
  --property "parse.key=true" \
  --property "key.separator=::"

# Input:
CoinDesk::{"id": "test-1", "title": "Test Article", "sentiment": {"score": 0.8}}

# Consommer des messages (depuis le début)
docker exec -it t-dat-kafka-1 /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:29092 \
  --topic rawarticle \
  --from-beginning \
  --property print.key=true \
  --property key.separator=" :: "

# Consommer (derniers messages uniquement)
docker exec -it t-dat-kafka-1 /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:29092 \
  --topic rawticker
```

### Python (confluent-kafka)

```python
from confluent_kafka import Producer, Consumer, KafkaError

# Configuration producteur
producer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'acks': '1',
    'retries': 3,
    'compression.type': 'lz4',
}

producer = Producer(producer_conf)

# Envoi message
producer.produce(
    topic='rawarticle',
    key='CoinDesk'.encode('utf-8'),
    value=json.dumps(payload).encode('utf-8'),
    callback=delivery_report
)
producer.flush()

# Configuration consommateur
consumer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'spark-job-ingestion',
    'auto.offset.reset': 'latest',  # 'earliest' pour re-jouer
    'enable.auto.commit': True,
}

consumer = Consumer(consumer_conf)
consumer.subscribe(['rawarticle'])

# Poll messages
while True:
    msg = consumer.poll(timeout=1.0)
    if msg is None:
        continue
    if msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
            continue
        else:
            raise KafkaException(msg.error())
    
    # Traitement
    key = msg.key().decode('utf-8')
    value = json.loads(msg.value().decode('utf-8'))
    print(f"Received: {key} -> {value}")
```

## Sérialisation

### Format des messages

Tous les messages utilisent **JSON UTF-8** avec une clé de partitionnement.

```
┌─────────────────────────────────────────────────────────────┐
│                      MESSAGE KAFKA                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Key: String (UTF-8 encoded)                              │
│   ├── rawarticle: source ("CoinDesk", "Cointelegraph", ...)  │
│   ├── rawticker: pair ("XBT/USD", "ETH/USD", ...)            │
│   ├── rawtrade: pair ("XBT/USD", ...)                        │
│   └── rawalert: pair ("XBT/USD", ...)                        │
│                                                             │
│   Value: JSON String (UTF-8 encoded)                         │
│   ├── rawarticle: Article payload                            │
│   ├── rawticker: Ticker payload                              │
│   ├── rawtrade: Trade payload                                │
│   └── rawalert: Alert payload                                │
│                                                             │
│   Headers: Optionnel (non utilisé)                           │
│                                                             │
│   Timestamp: Unix timestamp (ms)                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Exemples de payloads

```json
// rawarticle
{
  "id": "https://coindesk.com/article-123",
  "title": "Bitcoin Hits $100K",
  "url": "https://coindesk.com/article-123",
  "website": "CoinDesk",
  "summary": "Bitcoin reached...",
  "content": {"text": "..."},
  "published_at": 1705312800.123,
  "scraped_at": 1705312950.456,
  "tags": ["bitcoin", "btc"],
  "sentiment": {"score": 0.8234, "label": "positive"},
  "cryptocurrencies_mentioned": ["bitcoin", "btc"]
}

// rawticker
{
  "pair": "XBT/USD",
  "last": 99950.50,
  "bid": 99900.00,
  "ask": 100000.00,
  "volume_24h": 15000.5,
  "timestamp": 1705312345.678,
  "pct_change": 2.51
}

// rawtrade
{
  "pair": "XBT/USD",
  "price": 99950.50,
  "volume": 0.5,
  "timestamp": 1705312345.678,
  "side": "b"
}

// rawalert
{
  "pair": "XBT/USD",
  "type": "price_spike",
  "last": 99950.50,
  "change": 2.51,
  "threshold": 0.5,
  "timestamp": 1705312345.678
}
```

## Consumer Groups

### Spark Jobs et groupes

| Job | Group ID | Topics | Offset Strategy |
|-----|----------|--------|-----------------|
| kafka_to_timescale.py | spark-job-ingestion | rawarticle, rawticker, rawtrade, rawalert | latest |
| sentiment_prediction_job.py | spark-job-analytics | rawarticle, rawticker | latest |

### Commandes de gestion

```bash
# Lister les consumer groups
./kafka-consumer-groups.sh --bootstrap-server localhost:29092 --list

# Détails d'un groupe
./kafka-consumer-groups.sh --bootstrap-server localhost:29092 \
  --describe --group spark-job-ingestion

# Reset offset (re-jouer depuis le début)
./kafka-consumer-groups.sh --bootstrap-server localhost:29092 \
  --group spark-job-ingestion \
  --reset-offsets --to-earliest --execute \
  --topic rawarticle

# Reset offset (depuis une date)
./kafka-consumer-groups.sh --bootstrap-server localhost:29092 \
  --group spark-job-ingestion \
  --reset-offsets --to-datetime 2024-01-01T00:00:00.000 \
  --execute --topic rawarticle
```

## Monitoring et métriques

### Health check

```bash
# Vérifier disponibilité
./kafka-broker-api-versions.sh --bootstrap-server localhost:29092

# Statistiques topics
./kafka-topics.sh --bootstrap-server localhost:29092 --describe
```

### Métriques JMX (Prometheus)

```yaml
# kafka-exporter configuration
kafka_exporter:
  image: danielqsj/kafka-exporter:v1.8.0
  command:
    - '--kafka.server=kafka:29092'
  ports:
    - "9308:9308"
```

Métriques exposées:
- `kafka_topic_partition_current_offset`
- `kafka_consumergroup_lag`
- `kafka_topic_partition_in_sync_replica`

## Troubleshooting

### Problèmes courants

```bash
# 1. Topic n'existe pas
# → Le créer manuellement
./kafka-topics.sh --create --topic rawarticle --bootstrap-server localhost:29092

# 2. Consumer lag élevé
# → Vérifier performance Spark
./kafka-consumer-groups.sh --describe --group spark-job-ingestion

# 3. Messages non lus
# → Vérifier offset strategy
# → Reset offset si nécessaire

# 4. Connexion refusée
# → Vérifier listeners config
# → Vérifier firewall/réseau
```

### Logs

```bash
# Logs conteneur Kafka
docker logs t-dat-kafka-1 -f

# Logs debug (augmenter verbosité)
# Dans docker-compose:
environment:
  KAFKA_LOG4J_LOGGERS: "kafka.controller=INFO,kafka.producer.async.DefaultEventHandler=INFO"
```

---

**Suite** : [04-spark-streaming.md](./04-spark-streaming.md) pour les jobs de traitement.
