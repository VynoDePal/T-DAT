# 🚀 Configuration Kafka Locale - Implémentation Complète

## ✅ Changements Implémentés

Suite à l'analyse du dépôt [T-DAT-1](https://github.com/Izzoudine/T-DAT-1), le projet utilise maintenant **Kafka + Zookeeper locaux** au lieu d'un serveur Kafka distant.

---

## 📋 Approche T-DAT-1 Adoptée

### **Principe**
- **Kafka et Zookeeper** déployés localement via Docker Compose
- **Création automatique des topics** via script au démarrage
- **Environnement auto-suffisant** - pas de dépendance externe
- **Configuration optimisée** pour développement et production

### **Avantages**
✅ Contrôle total sur l'infrastructure  
✅ Reproductibilité garantie  
✅ Tests locaux simplifiés  
✅ Pas de dépendance réseau externe  
✅ Configuration flexible des topics  

---

## 🔧 Modifications Apportées

### **1. Docker Compose** (`docker-compose.yml`)

**Ajout de 2 nouveaux services :**

```yaml
services:
  # Zookeeper pour Kafka
  zookeeper:
    image: confluentinc/cp-zookeeper:7.7.0
    ports: 2181
    
  # Kafka pour streaming
  kafka:
    image: confluentinc/cp-kafka:7.7.0
    ports: 9092, 29092
    environment:
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'false'
```

**Configuration Kafka :**
- **Port externe** : `localhost:9092` (accès depuis l'hôte)
- **Port interne** : `kafka:29092` (accès depuis les conteneurs)
- **Auto-création désactivée** : les topics sont créés manuellement via script

---

### **2. Script de Création de Topics** (`scripts/create_kafka_topics.sh`)

**Topics créés automatiquement :**
- `rawticker` - Données de prix en temps réel (3 partitions)
- `rawtrade` - Transactions/trades (3 partitions)
- `rawarticle` - Articles de presse crypto (3 partitions)
- `rawalert` - Alertes de marché (3 partitions)

**Caractéristiques :**
- Utilise `--if-not-exists` pour éviter les erreurs
- Attend que Kafka soit complètement démarré (retry logic)
- Vérifie la création des topics

---

### **3. Configuration Mise à Jour**

#### **`.env` et `.env.example`**
```bash
# AVANT
KAFKA_SERVERS=20.199.136.163:9092

# APRÈS
KAFKA_SERVERS=localhost:9092
```

#### **`spark_jobs/config.py`**
```python
# AVANT
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_SERVERS', '20.199.136.163:9092')

# APRÈS
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_SERVERS', 'localhost:9092')
```

---

### **4. Workflow de Démarrage** (`scripts/start_all.sh`)

**Nouvelle séquence :**

```
1. Démarrer Zookeeper + Kafka + TimescaleDB + Redis (40s d'attente)
2. Créer automatiquement les topics Kafka
3. Initialiser TimescaleDB
4. Démarrer Django API
5. Démarrer les jobs Spark (ingestion + analytics)
```

**Délai d'attente :**
- Augmenté à **40 secondes** (au lieu de 30s) pour stabilisation complète de Kafka
- Inspiré de T-DAT-1 qui recommande 40s minimum

---

## 🎯 Utilisation

### **Démarrage Complet**

```bash
cd /home/kevyn-odjo/Documents/T-DAT

# Démarrer tous les services
./scripts/start_all.sh
```

**Ce qui se passe :**
1. ✅ Zookeeper démarre et se stabilise
2. ✅ Kafka démarre et se connecte à Zookeeper
3. ✅ Topics Kafka créés automatiquement (rawticker, rawtrade, rawarticle, rawalert)
4. ✅ TimescaleDB et Redis démarrent
5. ✅ Django API démarre avec migrations
6. ✅ Jobs Spark démarrent et se connectent à Kafka local

### **Vérification Kafka**

```bash
# Vérifier que Kafka est actif
docker exec crypto_viz_kafka kafka-broker-api-versions --bootstrap-server kafka:29092

# Lister les topics
docker exec crypto_viz_kafka kafka-topics --bootstrap-server kafka:29092 --list

# Voir les détails d'un topic
docker exec crypto_viz_kafka kafka-topics --bootstrap-server kafka:29092 --describe --topic rawticker
```

### **Arrêt**

```bash
./scripts/stop_all.sh
```

Arrête tous les services : Spark, Django, Kafka, Zookeeper, TimescaleDB, Redis.

---

## 📊 Architecture Finale

```
┌─────────────────────────────────────────────────────┐
│                  CRYPTO VIZ STACK                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Producteurs de Données]  (à implémenter)         │
│       │                                             │
│       ▼                                             │
│  ┌─────────────────────┐                           │
│  │  Kafka (port 9092)  │  ◄── Topics:              │
│  │  + Zookeeper (2181) │      - rawticker          │
│  └─────────────────────┘      - rawtrade           │
│       │                        - rawarticle         │
│       ▼                        - rawalert           │
│  ┌─────────────────────┐                           │
│  │   Spark Jobs        │                           │
│  │  - Ingestion        │                           │
│  │  - Analytics        │                           │
│  └─────────────────────┘                           │
│       │                                             │
│       ▼                                             │
│  ┌─────────────────────┐                           │
│  │ TimescaleDB (15432) │                           │
│  └─────────────────────┘                           │
│       │                                             │
│       ▼                                             │
│  ┌─────────────────────┐                           │
│  │  Django API (8000)  │                           │
│  │  + Redis (6380)     │                           │
│  └─────────────────────┘                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🔍 Comparaison Avant/Après

| Aspect | Avant | Après |
|--------|-------|-------|
| **Kafka** | Serveur distant (20.199.136.163) | Local Docker (localhost:9092) |
| **Topics** | Devaient exister sur serveur distant | Créés automatiquement au démarrage |
| **Dépendances** | Serveur Kafka externe requis | Auto-suffisant |
| **Reproductibilité** | Difficile (dépend du serveur) | Facile (tout en Docker) |
| **Configuration** | Fixe | Flexible et modifiable |
| **Problèmes** | Topics manquants → échec Spark | Tous les topics créés automatiquement |

---

## ⚙️ Configuration Avancée

### **Modifier les Topics**

Éditez `scripts/create_kafka_topics.sh` :

```bash
# Ajouter un nouveau topic
TOPICS=(
    "rawticker"
    "rawtrade"
    "rawarticle"
    "rawalert"
    "mon_nouveau_topic"  # ← Nouveau
)

# Modifier le nombre de partitions
PARTITIONS=5  # Au lieu de 3
```

### **Ajuster les Ressources Kafka**

Dans `docker-compose.yml` :

```yaml
kafka:
  environment:
    KAFKA_HEAP_OPTS: "-Xmx2G -Xms2G"  # Plus de mémoire
  mem_limit: 2.5g
```

---

## 🐛 Dépannage

### **Kafka ne démarre pas**

```bash
# Vérifier les logs
docker logs crypto_viz_kafka

# Augmenter le délai d'attente dans start_all.sh
sleep 60  # Au lieu de 40
```

### **Topics non créés**

```bash
# Créer manuellement
./scripts/create_kafka_topics.sh

# Ou individuellement
docker exec crypto_viz_kafka kafka-topics \
  --bootstrap-server kafka:29092 \
  --create --topic rawticker \
  --partitions 3 --replication-factor 1
```

### **Spark ne se connecte pas à Kafka**

```bash
# Vérifier la connexion
nc -zv localhost 9092

# Vérifier la config Spark
cat spark_jobs/config.py | grep KAFKA
```

---

## 📚 Ressources

- **Dépôt T-DAT-1** : https://github.com/Izzoudine/T-DAT-1
- **Confluent Kafka Docker** : https://docs.confluent.io/platform/current/installation/docker/
- **Spark Kafka Integration** : https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html

---

## ✨ Prochaines Étapes

1. **Implémenter les producteurs de données** (websocket Kraken, scraping articles)
2. **Tester le flux complet** : Producteur → Kafka → Spark → TimescaleDB → Django API
3. **Ajouter des métriques** de monitoring Kafka
4. **Configurer la persistance** des données Kafka (actuellement en volume Docker)

---

**Date de création** : 20 janvier 2026  
**Inspiré de** : T-DAT-1 par Izzoudine  
**Statut** : ✅ Implémenté et prêt à tester
