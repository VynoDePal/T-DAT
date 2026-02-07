"""
Django settings for crypto_viz project.
Configuration selon la stratégie d'intégration:
- SQLite pour métadonnées uniquement
- TimescaleDB pour séries temporelles (connexion externe)
- Django REST Framework pour APIs
"""

import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-change-this-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'corsheaders',
    'django_prometheus',
    'channels',
    
    # Local apps
    'api',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'crypto_viz.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'crypto_viz.wsgi.application'
ASGI_APPLICATION = 'crypto_viz.asgi.application'

# Database
# SQLite pour métadonnées Django uniquement (sessions, auth, config)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    # Configuration TimescaleDB pour séries temporelles
    # Cette connexion sera utilisée directement (sans ORM Django)
    'timescaledb': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('TIMESCALE_DB_NAME', 'crypto_viz_ts'),
        'USER': os.environ.get('TIMESCALE_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('TIMESCALE_DB_PASSWORD', 'password'),
        'HOST': os.environ.get('TIMESCALE_DB_HOST', 'timescaledb'),
        'PORT': os.environ.get('TIMESCALE_DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration for serving static files
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S.%fZ',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',
        'user': '5000/hour'
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# =============================================================================
# DRF-SPECTACULAR CONFIGURATION (Swagger/OpenAPI Documentation)
# =============================================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'CRYPTO VIZ API',
    'DESCRIPTION': '''
## 🚀 API de Visualisation de Crypto-monnaies en Temps Réel

### Description
CRYPTO VIZ est une plateforme complète de visualisation et d'analyse de crypto-monnaies 
offrant des données en temps réel, des analyses de sentiment et des prédictions de prix.

### Architecture
- **Backend**: Django REST Framework
- **Base de données**: TimescaleDB (séries temporelles) + SQLite (métadonnées)
- **Streaming**: Apache Kafka + Apache Spark
- **Cache**: Redis

### Sources de Données
Les données proviennent de plusieurs sources :
- **Prix temps réel**: Kraken WebSocket API
- **Articles crypto**: Scraping de sites spécialisés (CoinTelegraph, etc.)
- **Sentiment**: Analyse NLP des articles

### Authentification
Actuellement, l'API est ouverte (pas d'authentification requise).
Une authentification JWT sera implémentée dans une version future.

### Rate Limiting
- **Utilisateurs anonymes**: 100 requêtes/heure
- **Utilisateurs authentifiés**: 1000 requêtes/heure

### Formats de Données
- Toutes les réponses sont au format **JSON**
- Les timestamps sont au format **ISO 8601** (UTC)
- Les prix sont en **USD**

### Contact & Support
Pour toute question, ouvrez une issue sur le repository GitHub.
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    
    # Configuration Swagger UI
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
    
    # Swagger UI Settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'defaultModelsExpandDepth': 3,
        'defaultModelExpandDepth': 3,
        'docExpansion': 'list',
        'tagsSorter': 'alpha',
        'operationsSorter': 'alpha',
    },
    
    # Tags pour organiser les endpoints
    'TAGS': [
        {
            'name': 'Health',
            'description': 'Endpoints de vérification de santé du service'
        },
        {
            'name': 'Sentiment',
            'description': '''
**Analyse de Sentiment des Crypto-monnaies**

Ces endpoints fournissent l'historique du sentiment pour chaque crypto-monnaie.
Le sentiment est calculé à partir de l'analyse des articles de presse crypto.

**Score de sentiment:**
- `0.0 - 0.4`: Négatif 😟
- `0.4 - 0.6`: Neutre 😐
- `0.6 - 1.0`: Positif 😊
            '''
        },
        {
            'name': 'Predictions',
            'description': '''
**Prédictions de Prix**

Ces endpoints fournissent les prédictions de prix générées par nos modèles ML.

**Modèles disponibles:**
- `moving_average`: Moyenne mobile simple avec intervalles de confiance

**Données retournées:**
- Prix prédit
- Intervalles de confiance (bas/haut)
- Prix réel (si disponible pour comparaison)
            '''
        },
        {
            'name': 'Tickers',
            'description': '''
**Prix en Temps Réel (Tickers)**

Historique des prix pour les paires de trading crypto/USD.

**Paires supportées:**
- BTC/USD, ETH/USD, SOL/USD, ADA/USD
- MATIC/USD, DOT/USD, LINK/USD, USDT/USD

**Données retournées:**
- `last`: Dernier prix
- `bid`: Meilleure offre d'achat
- `ask`: Meilleure offre de vente
- `volume_24h`: Volume sur 24h
            '''
        },
        {
            'name': 'Trades',
            'description': '''
**Historique des Transactions**

Chaque transaction individuelle d'achat ou de vente.

**Données retournées:**
- `price`: Prix de la transaction
- `volume`: Volume échangé
- `side`: `b` (buy/achat) ou `s` (sell/vente)
            '''
        },
        {
            'name': 'Articles',
            'description': '''
**Articles Crypto avec Analyse de Sentiment**

Articles de presse crypto collectés et analysés automatiquement.

**Sources:**
- CoinTelegraph, CoinDesk, et autres sites spécialisés

**Données retournées:**
- Titre et URL de l'article
- Résumé du contenu
- Crypto-monnaies mentionnées
- Score et label de sentiment
            '''
        },
        {
            'name': 'Alerts',
            'description': '''
**Alertes de Variation de Prix**

Alertes générées automatiquement lors de variations significatives de prix.

**Types d'alertes:**
- `PRICE_UP`: Hausse significative (> seuil)
- `PRICE_DOWN`: Baisse significative (> seuil)

**Seuil par défaut:** 1% de variation
            '''
        },
        {
            'name': 'Configuration',
            'description': '''
**Configuration Utilisateur**

Gestion des crypto-monnaies suivies et des paramètres de visualisation.

**Fonctionnalités:**
- Ajouter/supprimer des cryptos à suivre
- Sauvegarder des configurations de graphiques
- Personnaliser les indicateurs techniques
            '''
        },
        {
            'name': 'WebSocket',
            'description': '''
**Streaming Temps Réel via WebSocket**

Les endpoints WebSocket permettent de recevoir des données en continu sans polling.
Utilisez `periode=live` sur les routes REST pour obtenir l'URL WebSocket correspondante.

**Architecture:** Kafka → Redis Channel Layer → Django Channels → Client

---

### `ws/ticker/<base>/<quote>/` — Prix temps réel

Source Kafka : `rawticker`

```json
{
  "pair": "BTC/USD",
  "last": 98500.50,
  "bid": 98499.00,
  "ask": 98501.00,
  "volume_24h": 1234.56,
  "timestamp": "2026-02-06T13:00:00Z"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `pair` | string | Paire de trading (ex: `BTC/USD`) |
| `last` | float | Dernier prix de transaction |
| `bid` | float | Meilleure offre d\'achat |
| `ask` | float | Meilleure offre de vente |
| `volume_24h` | float | Volume échangé sur 24h |
| `timestamp` | string | Horodatage ISO 8601 |

---

### `ws/trade/<base>/<quote>/` — Transactions temps réel

Source Kafka : `rawtrade`

```json
{
  "pair": "BTC/USD",
  "price": 98500.50,
  "volume": 0.5,
  "side": "b",
  "timestamp": "2026-02-06T13:00:00Z"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `pair` | string | Paire de trading |
| `price` | float | Prix de la transaction |
| `volume` | float | Volume échangé |
| `side` | string | `b` = achat, `s` = vente |
| `timestamp` | string | Horodatage ISO 8601 |

---

### `ws/sentiment/<symbol>/` — Sentiment temps réel

Source Kafka : `rawarticle` (articles analysés par NLP)

```json
{
  "crypto_symbol": "BTC",
  "sentiment_score": 0.85,
  "sentiment_label": "positive",
  "title": "Bitcoin hits new highs...",
  "website": "cointelegraph.com"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `crypto_symbol` | string | Symbole de la crypto |
| `sentiment_score` | float | Score de sentiment (0.0 à 1.0) |
| `sentiment_label` | string | `positive`, `neutral` ou `negative` |
| `title` | string | Titre de l\'article source |
| `website` | string | Site web source |

---

### `ws/prediction/<symbol>/` — Prédictions

> **Note :** Ce consumer est prêt mais n\'est pas encore alimenté en temps réel.
> Les prédictions sont générées par Spark et disponibles via l\'API REST historique.

---

### `ws/alert/` — Alertes de prix temps réel

Source Kafka : `rawalert`

```json
{
  "pair": "BTC/USD",
  "last_price": 98500.00,
  "change_percent": 1.5,
  "threshold": 1.0,
  "alert_type": "PRICE_UP",
  "timestamp": "2026-02-06T13:00:00Z"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `pair` | string | Paire concernée |
| `last_price` | float | Prix au moment de l\'alerte |
| `change_percent` | float | Variation en % |
| `threshold` | float | Seuil de déclenchement |
| `alert_type` | string | `PRICE_UP` ou `PRICE_DOWN` |
| `timestamp` | string | Horodatage ISO 8601 |

---

### Connexion JavaScript

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/ticker/BTC/USD/');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Prix:', data.last, 'Bid:', data.bid, 'Ask:', data.ask);
};
ws.onclose = () => console.log('Déconnecté');
```
            '''
        },
    ],
    
    # Composants réutilisables
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    
    # Exemples
    'EXAMPLES_INCLUDE_OPTIONALS': True,
    
    # Schéma
    'SCHEMA_PATH_PREFIX': '/api/v1',
    'SCHEMA_PATH_PREFIX_TRIM': False,
    
    # Extensions
    'EXTENSIONS_INFO': {
        'x-logo': {
            'url': 'https://example.com/logo.png',
            'altText': 'CRYPTO VIZ Logo'
        }
    },
    
    # Contact
    'CONTACT': {
        'name': 'CRYPTO VIZ Team',
        'email': 'support@cryptoviz.com',
        'url': 'https://github.com/cryptoviz'
    },
    
    # License
    'LICENSE': {
        'name': 'MIT License',
        'url': 'https://opensource.org/licenses/MIT'
    },
    
    # Servers
    'SERVERS': [
        {
            'url': os.environ.get('API_BASE_URL', 'http://localhost:8000'),
            'description': 'Serveur API'
        },
        {
            'url': f"http://{os.environ.get('HOST_IP', '192.168.218.62')}:8000",
            'description': 'Serveur réseau local (accès depuis autres machines)'
        },
        {
            'url': 'http://localhost:8000',
            'description': 'Serveur de développement local'
        },
        {
            'url': 'http://127.0.0.1:8000',
            'description': 'Serveur local alternatif'
        },
    ],
    
    # External docs
    'EXTERNAL_DOCS': {
        'description': 'Documentation complète du projet',
        'url': 'https://github.com/cryptoviz/docs'
    },
}

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True  # À restreindre en production

# Redis Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')

# Django Channels — Channel Layer via Redis
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, int(REDIS_PORT))],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_SERVERS', 'kafka:29092')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'crypto_viz',
        'TIMEOUT': 300,  # 5 minutes par défaut
    }
}

# Cache pour les sessions Django
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_SERVERS', '20.199.136.163:9092')
KAFKA_TOPICS = {
    'TICKER': 'rawticker',
    'TRADE': 'rawtrade',
    'ARTICLE': 'rawarticle',
    'ALERT': 'rawalert',
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
