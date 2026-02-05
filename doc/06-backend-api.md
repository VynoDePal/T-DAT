# Django REST API - Backend

## Vue d'ensemble

Le backend Django fournit une **API REST** pour consommer les données analytiques stockées dans TimescaleDB. Il utilise Django REST Framework (DRF) pour la sérialisation et expose des endpoints optimisés pour les séries temporelles.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DJANGO REST API                                 │
│                    (Django 4.2 + Django REST Framework)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                        URL Routing (urls.py)                        │ │
│   │                                                                     │ │
│   │  /api/v1/sentiment/<crypto>/historique/?periode=7d                  │ │
│   │  /api/v1/prix/<crypto>/historique/                                  │ │
│   │  /api/v1/prix/<crypto>/temps_reel/                                  │ │
│   │  /api/v1/predictions/<crypto>/                                       │ │
│   │  /api/v1/articles/<crypto>/                                         │ │
│   │  /api/v1/alertes/                                                   │ │
│   │                                                                     │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
│                              │                                          │
│                              ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                        Views (views.py)                              │ │
│   │                                                                     │ │
│   │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │ │
│   │  │  Sentiment    │  │    Prix       │  │  Predictions  │            │ │
│   │  │  Historique   │  │  Historique   │  │               │            │ │
│   │  │  View         │  │  View         │  │  View         │            │ │
│   │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘            │ │
│   │          │                  │                  │                     │ │
│   │          └──────────────────┼──────────────────┘                     │ │
│   │                             │                                        │ │
│   │                             ▼                                        │ │
│   │  ┌─────────────────────────────────────────────────────────────┐   │ │
│   │  │                    TimescaleClient (timescale_client.py)       │   │ │
│   │  │                                                                │   │ │
│   │  │  • Raw SQL optimisé pour TimescaleDB                          │   │ │
│   │  │  • time_bucket() pour agrégation temporelle                    │   │ │
│   │  │  • Index-aware queries                                        │   │ │
│   │  │                                                                │   │ │
│   │  │  SQL Exemple:                                                  │   │ │
│   │  │  SELECT time_bucket('1h', timestamp), AVG(score)             │   │ │
│   │  │  FROM sentiment_data                                           │   │ │
│   │  │  WHERE crypto_symbol = %s                                      │   │ │
│   │  │  GROUP BY bucket ORDER BY bucket DESC                         │   │ │
│   │  │                                                                │   │ │
│   │  └─────────────────────────────────────────────────────────────┘   │ │
│   │                             │                                        │ │
│   │                             ▼                                        │ │
│   │  ┌─────────────────────────────────────────────────────────────┐   │ │
│   │  │                    PostgreSQL/TimescaleDB                    │   │ │
│   │  │                     (localhost:15432)                          │   │ │
│   │  └─────────────────────────────────────────────────────────────┘   │ │
│   │                                                                     │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Architecture Django

### Configuration

```python
# crypto_viz_backend/crypto_viz/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('TIMESCALE_DB_NAME', 'crypto_viz_ts'),
        'USER': os.environ.get('TIMESCALE_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('TIMESCALE_DB_PASSWORD', 'password'),
        'HOST': os.environ.get('TIMESCALE_DB_HOST', 'localhost'),
        'PORT': os.environ.get('TIMESCALE_DB_PORT', '15432'),
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'api',  # Notre application
]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
}
```

### Routing (urls.py)

```python
# crypto_viz_backend/api/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Sentiment
    path(
        'sentiment/<str:crypto>/historique/',
        views.SentimentHistoriqueView.as_view(),
        name='sentiment-historique'
    ),
    
    # Prix
    path(
        'prix/<str:crypto>/historique/',
        views.PrixHistoriqueView.as_view(),
        name='prix-historique'
    ),
    path(
        'prix/<str:crypto>/temps_reel/',
        views.PrixTempsReelView.as_view(),
        name='prix-temps-reel'
    ),
    
    # Prédictions
    path(
        'predictions/<str:crypto>/',
        views.PredictionsView.as_view(),
        name='predictions'
    ),
    
    # Articles
    path(
        'articles/<str:crypto>/',
        views.ArticlesView.as_view(),
        name='articles'
    ),
    
    # Alertes
    path(
        'alertes/',
        views.AlertesView.as_view(),
        name='alertes'
    ),
]
```

## TimescaleClient

Le `TimescaleClient` fournit une abstraction pour les requêtes SQL optimisées TimescaleDB.

```python
# crypto_viz_backend/api/timescale_client.py

import psycopg2
from django.conf import settings
from typing import List, Dict, Optional

class TimescaleClient:
    """
    Client pour exécuter des requêtes optimisées TimescaleDB.
    """
    
    def __init__(self):
        self.connection_params = {
            'host': settings.DATABASES['default']['HOST'],
            'port': settings.DATABASES['default']['PORT'],
            'database': settings.DATABASES['default']['NAME'],
            'user': settings.DATABASES['default']['USER'],
            'password': settings.DATABASES['default']['PASSWORD'],
        }
    
    def _get_connection(self):
        """Crée une connexion PostgreSQL."""
        return psycopg2.connect(**self.connection_params)
    
    def query_sentiment_historique(
        self, 
        crypto: str, 
        periode: str = '7d',
        bucket_interval: str = '1 hour'
    ) -> List[Dict]:
        """
        Récupère l'historique de sentiment agrégé par intervalle temporel.
        
        Args:
            crypto: Symbole crypto (ex: 'bitcoin', 'btc')
            periode: Période (1h, 24h, 7d, 30d)
            bucket_interval: Intervalle d'agrégation
        """
        sql = """
            SELECT 
                time_bucket(%s, timestamp) as bucket,
                AVG(sentiment_score) as avg_sentiment_score,
                COUNT(*) as article_count,
                MODE() WITHIN GROUP (ORDER BY sentiment_label) as dominant_label,
                AVG(confidence) as avg_confidence
            FROM sentiment_data
            WHERE crypto_symbol ILIKE %s
              AND timestamp > NOW() - INTERVAL %s
            GROUP BY bucket
            ORDER BY bucket DESC
        """
        
        params = (
            bucket_interval,
            f'%{crypto}%',
            periode
        )
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [desc[0] for desc in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                return results
    
    def query_prix_temps_reel(self, crypto: str) -> Optional[Dict]:
        """
        Récupère le dernier prix connu pour une crypto.
        
        Args:
            crypto: Symbole ou nom (ex: 'BTC', 'bitcoin')
        """
        sql = """
            SELECT 
                pair,
                last as last_price,
                bid as bid_price,
                ask as ask_price,
                volume_24h,
                timestamp,
                pct_change
            FROM ticker_data
            WHERE pair ILIKE %s
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        # Mapping crypto vers paire
        pair_pattern = self._crypto_to_pair_pattern(crypto)
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (pair_pattern,))
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    def query_prix_historique(
        self,
        crypto: str,
        periode: str = '24h',
        bucket_interval: str = '5 minutes'
    ) -> List[Dict]:
        """
        Récupère l'historique des prix avec agrégation OHLCV.
        
        Args:
            crypto: Symbole crypto
            periode: Période d'historique
            bucket_interval: Intervalle de bougie (candle)
        """
        sql = """
            SELECT 
                time_bucket(%s, timestamp) as bucket,
                pair,
                first(last, timestamp) as open_price,
                MAX(last) as high_price,
                MIN(last) as low_price,
                last(last, timestamp) as close_price,
                AVG(volume_24h) as avg_volume,
                COUNT(*) as tick_count
            FROM ticker_data
            WHERE pair ILIKE %s
              AND timestamp > NOW() - INTERVAL %s
            GROUP BY bucket, pair
            ORDER BY bucket DESC
        """
        
        params = (
            bucket_interval,
            self._crypto_to_pair_pattern(crypto),
            periode
        )
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [desc[0] for desc in cursor.description]
                return [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
    
    def query_predictions(self, crypto: str, limit: int = 100) -> List[Dict]:
        """
        Récupère les prédictions de prix avec métriques de confiance.
        """
        sql = """
            SELECT 
                timestamp,
                crypto_symbol,
                predicted_price,
                actual_price,
                model_name,
                confidence_interval_low,
                confidence_interval_high,
                (confidence_interval_high - confidence_interval_low) as confidence_range,
                CASE 
                    WHEN actual_price IS NOT NULL THEN
                        ABS((actual_price - predicted_price) / actual_price * 100)
                    ELSE NULL
                END as error_percent
            FROM prediction_data
            WHERE crypto_symbol ILIKE %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (f'%{crypto}%', limit))
                columns = [desc[0] for desc in cursor.description]
                return [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
    
    def query_articles(
        self,
        crypto: str,
        limit: int = 50,
        sentiment_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Récupère les articles liés à une crypto avec filtrage optionnel.
        """
        base_sql = """
            SELECT 
                article_id,
                title,
                url,
                website,
                summary,
                sentiment_score,
                sentiment_label,
                timestamp,
                cryptocurrencies_mentioned
            FROM article_data
            WHERE (%s = ANY(cryptocurrencies_mentioned)
                   OR title ILIKE %s
                   OR summary ILIKE %s)
        """
        
        params = [crypto, f'%{crypto}%', f'%{crypto}%']
        
        if sentiment_filter:
            base_sql += " AND sentiment_label = %s"
            params.append(sentiment_filter)
        
        base_sql += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(base_sql, params)
                columns = [desc[0] for desc in cursor.description]
                return [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
    
    def query_alertes(
        self,
        crypto: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Récupère les alertes de prix récentes.
        """
        if crypto:
            sql = """
                SELECT 
                    timestamp,
                    pair,
                    last_price,
                    change_percent,
                    alert_type,
                    threshold
                FROM alert_data
                WHERE pair ILIKE %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params = (f'%{crypto}%', limit)
        else:
            sql = """
                SELECT 
                    timestamp,
                    pair,
                    last_price,
                    change_percent,
                    alert_type,
                    threshold
                FROM alert_data
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params = (limit,)
        
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [desc[0] for desc in cursor.description]
                return [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
    
    def _crypto_to_pair_pattern(self, crypto: str) -> str:
        """
        Convertit un symbole crypto en pattern de recherche pour les paires.
        
        Ex: 'bitcoin' → '%XBT%', 'btc' → '%XBT%', 'eth' → '%ETH%'
        """
        crypto_upper = crypto.upper()
        
        # Mapping des noms vers symboles Kraken
        mappings = {
            'BITCOIN': '%XBT%',
            'BTC': '%XBT%',
            'ETHEREUM': '%ETH%',
            'ETH': '%ETH%',
            'SOLANA': '%SOL%',
            'SOL': '%SOL%',
            'CARDANO': '%ADA%',
            'ADA': '%ADA%',
            'POLYGON': '%MATIC%',
            'MATIC': '%MATIC%',
            'POLKADOT': '%DOT%',
            'DOT': '%DOT%',
            'CHAINLINK': '%LINK%',
            'LINK': '%LINK%',
            'TETHER': '%USDT%',
            'USDT': '%USDT%',
        }
        
        return mappings.get(crypto_upper, f'%{crypto_upper}%')
```

## Views (Endpoints)

```python
# crypto_viz_backend/api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404

from .timescale_client import TimescaleClient


class SentimentHistoriqueView(APIView):
    """
    GET /api/v1/sentiment/<crypto>/historique/?periode=7d&bucket=1h
    
    Retourne l'historique de sentiment agrégé par intervalle temporel.
    """
    
    def get(self, request, crypto):
        # Paramètres
        periode = request.query_params.get('periode', '7d')
        bucket = request.query_params.get('bucket', '1 hour')
        
        # Validation
        valid_periodes = ['1h', '24h', '7d', '30d']
        if periode not in valid_periodes:
            return Response(
                {'error': f'Période invalide. Choix: {valid_periodes}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Requête
        client = TimescaleClient()
        data = client.query_sentiment_historique(
            crypto=crypto,
            periode=periode,
            bucket_interval=bucket
        )
        
        return Response({
            'crypto_symbol': crypto.upper(),
            'count': len(data),
            'periode': periode,
            'bucket_interval': bucket,
            'data': data
        })


class PrixTempsReelView(APIView):
    """
    GET /api/v1/prix/<crypto>/temps_reel/
    
    Retourne le dernier prix connu pour une crypto.
    """
    
    def get(self, request, crypto):
        client = TimescaleClient()
        data = client.query_prix_temps_reel(crypto)
        
        if not data:
            raise Http404(f'Aucune donnée pour {crypto}')
        
        return Response({
            'crypto_symbol': crypto.upper(),
            'data': data
        })


class PrixHistoriqueView(APIView):
    """
    GET /api/v1/prix/<crypto>/historique/?periode=24h&bucket=5m
    
    Retourne l'historique des prix avec agrégation OHLCV.
    """
    
    def get(self, request, crypto):
        periode = request.query_params.get('periode', '24h')
        bucket = request.query_params.get('bucket', '5 minutes')
        
        client = TimescaleClient()
        data = client.query_prix_historique(
            crypto=crypto,
            periode=periode,
            bucket_interval=bucket
        )
        
        return Response({
            'crypto_symbol': crypto.upper(),
            'count': len(data),
            'data': data
        })


class PredictionsView(APIView):
    """
    GET /api/v1/predictions/<crypto>/?limit=100
    
    Retourne les prédictions de prix avec métriques.
    """
    
    def get(self, request, crypto):
        limit = int(request.query_params.get('limit', 100))
        limit = min(limit, 1000)  # Max 1000
        
        client = TimescaleClient()
        data = client.query_predictions(crypto, limit)
        
        return Response({
            'crypto_symbol': crypto.upper(),
            'count': len(data),
            'data': data
        })


class ArticlesView(APIView):
    """
    GET /api/v1/articles/<crypto>/?limit=50&sentiment=positive
    
    Retourne les articles liés à une crypto.
    """
    
    def get(self, request, crypto):
        limit = int(request.query_params.get('limit', 50))
        sentiment = request.query_params.get('sentiment')
        
        client = TimescaleClient()
        data = client.query_articles(
            crypto=crypto,
            limit=limit,
            sentiment_filter=sentiment
        )
        
        return Response({
            'crypto_symbol': crypto.upper(),
            'count': len(data),
            'data': data
        })


class AlertesView(APIView):
    """
    GET /api/v1/alertes/?crypto=BTC&limit=20
    
    Retourne les alertes de prix récentes.
    """
    
    def get(self, request):
        crypto = request.query_params.get('crypto')
        limit = int(request.query_params.get('limit', 20))
        
        client = TimescaleClient()
        data = client.query_alertes(crypto, limit)
        
        return Response({
            'count': len(data),
            'data': data
        })
```

## Exemples de réponses API

### Sentiment historique

```json
{
  "crypto_symbol": "BITCOIN",
  "count": 168,
  "periode": "7d",
  "bucket_interval": "1 hour",
  "data": [
    {
      "bucket": "2024-01-15T14:00:00+00:00",
      "avg_sentiment_score": 0.7523,
      "article_count": 5,
      "dominant_label": "positive",
      "avg_confidence": 0.8123
    },
    {
      "bucket": "2024-01-15T13:00:00+00:00",
      "avg_sentiment_score": 0.6123,
      "article_count": 3,
      "dominant_label": "positive",
      "avg_confidence": 0.7234
    }
  ]
}
```

### Prix temps réel

```json
{
  "crypto_symbol": "BTC",
  "data": {
    "pair": "XBT/USD",
    "last_price": 99950.50,
    "bid_price": 99900.00,
    "ask_price": 100000.00,
    "volume_24h": 15000.5,
    "timestamp": "2024-01-15T14:30:00+00:00",
    "pct_change": 2.51
  }
}
```

### Prédictions

```json
{
  "crypto_symbol": "BTC",
  "count": 100,
  "data": [
    {
      "timestamp": "2024-01-15T14:30:00+00:00",
      "crypto_symbol": "BTC",
      "predicted_price": 99950.50,
      "actual_price": 99950.50,
      "model_name": "moving_average",
      "confidence_interval_low": 99450.50,
      "confidence_interval_high": 100450.50,
      "confidence_range": 1000.00,
      "error_percent": 0.0
    }
  ]
}
```

## Tests API

```bash
# Test sentiment
curl "http://localhost:8000/api/v1/sentiment/bitcoin/historique/?periode=7d"

# Test prix temps réel
curl "http://localhost:8000/api/v1/prix/btc/temps_reel/"

# Test historique prix
curl "http://localhost:8000/api/v1/prix/eth/historique/?periode=24h"

# Test prédictions
curl "http://localhost:8000/api/v1/predictions/btc/?limit=10"

# Test articles avec filtre sentiment
curl "http://localhost:8000/api/v1/articles/bitcoin/?limit=10&sentiment=positive"

# Test alertes
curl "http://localhost:8000/api/v1/alertes/?crypto=BTC&limit=5"
```

---

**Suite** : [07-deployment.md](./07-deployment.md) pour le guide de déploiement.
