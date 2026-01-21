# Architecture Technique - CRYPTO VIZ

Ce document détaille l'architecture technique du système CRYPTO VIZ.

## 📐 Vue d'Ensemble de l'Architecture

### Diagramme de Flux de Données

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOURCES DE DONNÉES                          │
│                    (Serveur Kafka Externe)                      │
│                   20.199.136.163:9092                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
    ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
    │ rawticker │    │ rawtrade  │    │rawarticle │
    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
          │                │                 │
          └────────────────┼─────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                                 │
    ┌─────▼──────────┐            ┌────────▼────────┐
    │  SPARK JOB 1   │            │   SPARK JOB 2   │
    │  Ingestion     │            │   Analytics     │
    │  - Ticker      │            │   - Sentiment   │
    │  - Trade       │            │   - Prediction  │
    │  - Article     │            │                 │
    │  - Alert       │            │                 │
    └─────┬──────────┘            └────────┬────────┘
          │                                │
          └────────────────┬───────────────┘
                           │
                    ┌──────▼──────┐
                    │ TimescaleDB │
                    │ (PostgreSQL)│
                    │  Hypertables│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Django    │
                    │  REST API   │
                    │ (+ SQLite)  │
                    └──────┬──────┘
                           │
                ┌──────────┼──────────┐
                │                     │
         ┌──────▼──────┐      ┌──────▼──────┐
         │   HTTP API  │      │  WebSocket  │
         │   (REST)    │      │  (Channels) │
         └──────┬──────┘      └──────┬──────┘
                │                     │
                └──────────┬──────────┘
                           │
                    ┌──────▼──────┐
                    │  Frontend   │
                    │ (React/Vue) │
                    └─────────────┘
```

## 🔧 Composants Détaillés

### 1. Sources de Données (Kafka Topics)

#### rawticker
**Fonction** : Prix en temps réel des crypto-monnaies

**Format** :
```json
{
  "pair": "BTC/USD",
  "last": 34000.12,
  "bid": 33990.00,
  "ask": 34010.00,
  "volume_24h": 1200.5,
  "timestamp": 1764310291
}
```

**Fréquence** : Temps réel (plusieurs fois par seconde)

#### rawtrade
**Fonction** : Transactions individuelles d'achat/vente

**Format** :
```json
{
  "pair": "ETH/USD",
  "price": 2400.5,
  "volume": 2.1,
  "timestamp": 1764310292,
  "side": "b"
}
```

**Fréquence** : Temps réel (à chaque transaction)

#### rawarticle
**Fonction** : Articles de presse crypto avec analyse de sentiment

**Format** :
```json
{
  "id": "cointelegraph_1764313285",
  "title": "Bitcoiners accuse JPMorgan...",
  "url": "https://cointelegraph.com/news/...",
  "website": "cointelegraph.com",
  "content": {"summary": "..."},
  "cryptocurrencies_mentioned": ["BTC","ETH"],
  "sentiment": {
    "score": 0.993,
    "label": "positive"
  }
}
```

**Fréquence** : Quasi temps réel (scraping périodique)

#### rawalert
**Fonction** : Alertes de variation de prix significative

**Format** :
```json
{
  "pair": "BTC/USD",
  "last": 34000,
  "change": 1.2,
  "threshold": 1,
  "timestamp": 1764310293
}
```

**Fréquence** : Événementiel (quand seuil dépassé)

---

### 2. Couche de Traitement (Apache Spark)

#### Job 1 : Ingestion (`kafka_to_timescale.py`)

**Responsabilités** :
- Consommer les 4 topics Kafka
- Parser et valider les données JSON
- Transformer les timestamps
- Écrire dans TimescaleDB via JDBC

**Configuration** :
- Mode : Structured Streaming
- Checkpoint : `/tmp/spark_checkpoints/`
- Trigger : Processing time (micro-batches)

**Tables de destination** :
- `ticker_data`
- `trade_data`
- `article_data`
- `alert_data`

#### Job 2 : Analytics (`sentiment_prediction_job.py`)

**Responsabilités** :
- Analyser le sentiment agrégé par crypto
- Générer des prédictions de prix
- Calculer des métriques avancées

**Algorithmes** :
- Sentiment : Agrégation par fenêtre temporelle (5 min)
- Prédiction : Moyenne mobile + intervalles de confiance

**Tables de destination** :
- `sentiment_data`
- `prediction_data`

**Fenêtres temporelles** :
- Fenêtre de traitement : 5 minutes
- Watermark : 10 minutes

---

### 3. Couche de Stockage

#### TimescaleDB (Séries Temporelles)

**Rôle** : Stockage optimisé des données temporelles

**Tables hypertables** :

| Table | Description | Index Principaux | Rétention |
|-------|-------------|------------------|-----------|
| `ticker_data` | Prix temps réel | (pair, timestamp) | 90 jours |
| `trade_data` | Transactions | (pair, timestamp), (side) | 90 jours |
| `article_data` | Articles | (timestamp), (cryptos), (sentiment) | 90 jours |
| `alert_data` | Alertes | (pair, timestamp), (type) | 90 jours |
| `sentiment_data` | Sentiment agrégé | (crypto, timestamp) | 90 jours |
| `prediction_data` | Prédictions | (crypto, timestamp), (model) | 90 jours |

**Vues matérialisées** :
- `sentiment_hourly` : Sentiment moyen horaire
- `ticker_ohlc_hourly` : OHLC (Open/High/Low/Close) horaire

**Optimisations** :
- Compression automatique des chunks anciens
- Politiques de rétention (90 jours)
- Agrégations continues
- Index optimisés pour requêtes temporelles

#### SQLite (Métadonnées Django)

**Rôle** : Stockage léger pour données non critiques

**Tables** :
- `crypto_configuration` : Configuration des cryptos suivies
- `visualization_parameters` : Paramètres utilisateur
- `data_cache` : Cache temporaire de résultats

**Pourquoi SQLite ?**
- ✅ Suffisant pour métadonnées
- ✅ Pas de dépendance externe
- ✅ Configuration simple
- ❌ Ne gère PAS les données temporelles

---

### 4. Couche API (Django REST Framework)

#### Architecture Django

```
crypto_viz/          # Projet Django
├── settings.py      # Configuration (SQLite + TimescaleDB)
├── urls.py          # Routes principales
└── wsgi.py          # WSGI application

api/                 # Application API
├── models.py        # Modèles SQLite (métadonnées)
├── serializers.py   # Serializers DRF
├── views.py         # Vues API REST
├── timescale_client.py  # Client TimescaleDB
└── urls.py          # Routes API
```

#### Endpoints Principaux

**Configuration (SQLite)** :
```
GET    /api/v1/config/crypto/
POST   /api/v1/config/crypto/
GET    /api/v1/config/visualization/
```

**Données Historiques (TimescaleDB)** :
```
GET    /api/v1/sentiment/{symbol}/historique/
GET    /api/v1/prediction/{symbol}/historique/
GET    /api/v1/ticker/{pair}/historique/
GET    /api/v1/trade/{pair}/historique/
GET    /api/v1/article/historique/
GET    /api/v1/alert/historique/
```

**Paramètres de requête** :
- `periode` : 1h, 24h, 7d, 30d
- `date_debut` : Date ISO 8601
- `date_fin` : Date ISO 8601

#### Stratégie de Connexion

**SQLite** (via ORM Django) :
```python
# Utilisé par défaut pour les modèles Django
CryptoConfiguration.objects.all()
```

**TimescaleDB** (connexion directe) :
```python
# Via psycopg2 sans ORM
from api.timescale_client import timescale_client
data = timescale_client.get_sentiment_history('BTC', '24h')
```

---

### 5. Temps Réel (WebSocket)

**Option 1** : API WebSocket Externe (existante)
- URL : `ws://20.199.136.163:8000/ws/raw-ticker`
- Lecture directe depuis Kafka
- ✅ Recommandée si performante

**Option 2** : Django Channels (à implémenter)
- Consumer Django s'abonne à Kafka
- Retransmet via Channel Layer (Redis)
- Permet logique métier supplémentaire

---

## 🔄 Flux de Données Détaillé

### Exemple : Prix BTC/USD

1. **Kafka** : Message publié sur `rawticker`
   ```json
   {"pair": "BTC/USD", "last": 34000, ...}
   ```

2. **Spark Ingestion** : 
   - Lit depuis Kafka
   - Parse JSON
   - Valide les données
   - Écrit dans `ticker_data`

3. **Spark Analytics** :
   - Agrège sur fenêtre 5 min
   - Calcule prédiction (moyenne mobile)
   - Écrit dans `prediction_data`

4. **TimescaleDB** :
   - Stocke dans hypertable
   - Compression automatique
   - Index pour requêtes rapides

5. **Django API** :
   - Client frontend requête `/api/v1/ticker/BTC/USD/historique/?periode=1h`
   - Django interroge TimescaleDB
   - Retourne JSON sérialisé

6. **Frontend** :
   - Affiche graphique des prix
   - Met à jour en temps réel via WebSocket

---

## 🚀 Performance et Scalabilité

### Optimisations Actuelles

**TimescaleDB** :
- Chunks de 7 jours
- Compression après 7 jours
- Rétention automatique (90 jours)
- Index sur colonnes fréquemment requêtées

**Spark** :
- Micro-batches pour faible latence
- Checkpointing pour reprise sur erreur
- Watermarks pour gestion des données tardives

**Django** :
- Pagination (100 items par page)
- Cache potentiel avec Redis
- Connexion pooling pour TimescaleDB

### Limites et Scalabilité

**Goulots d'étranglement potentiels** :

1. **Écriture TimescaleDB** :
   - Limitation : ~10k inserts/sec (single node)
   - Solution : Cluster TimescaleDB + sharding

2. **Requêtes API Django** :
   - Limitation : ~100 req/sec (single instance)
   - Solution : Load balancer + instances multiples

3. **Spark Processing** :
   - Limitation : Dépend des ressources (local[*])
   - Solution : Cluster Spark (YARN, Kubernetes)

**Recommandations pour Production** :

- TimescaleDB : Cluster multi-nodes
- Django : Déploiement multi-instances (Kubernetes)
- Spark : Cluster dédié
- Cache : Redis pour résultats fréquents
- CDN : Pour assets frontend

---

## 🔒 Sécurité

### Implémenté

- Variables d'environnement pour credentials
- CORS configuré (à restreindre en prod)
- SQLite pour données non sensibles
- Validation des entrées API

### À Implémenter

- [ ] Authentification JWT
- [ ] Rate limiting
- [ ] HTTPS obligatoire
- [ ] Secrets management (Vault)
- [ ] Audit logs

---

## 📊 Monitoring et Logs

### Logs Actuels

- Django : `logs/django.log`
- Spark Ingestion : `logs/spark_ingestion.log`
- Spark Analytics : `logs/spark_analytics.log`
- TimescaleDB : Docker logs

### Métriques Recommandées

**Application** :
- Nombre de requêtes API
- Latence des requêtes
- Taux d'erreur

**Base de données** :
- Nombre de rows par table
- Taille des chunks TimescaleDB
- Temps de requête moyen

**Spark** :
- Records traités/sec
- Lag Kafka
- Taux d'échec des batches

### Outils Recommandés

- **Prometheus** : Métriques
- **Grafana** : Dashboards
- **ELK Stack** : Logs centralisés
- **Spark UI** : Monitoring Spark

---

## 🧪 Tests

### Types de Tests

**Tests Unitaires** :
- Modèles Django
- Serializers
- Fonctions utilitaires

**Tests d'Intégration** :
- APIs REST
- Client TimescaleDB
- Jobs Spark (mini-batches)

**Tests de Performance** :
- Charge API (Locust, JMeter)
- Ingestion Spark (volumes)
- Requêtes TimescaleDB

### À Implémenter

```bash
# Django
python manage.py test

# Spark (avec pytest)
pytest spark_jobs/tests/
```

---

## 📚 Références

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Apache Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Kafka Python Client](https://kafka-python.readthedocs.io/)

---

**Version** : 1.0.0  
**Date** : Novembre 2024  
**Auteur** : CRYPTO VIZ Team
