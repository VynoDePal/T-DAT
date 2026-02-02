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
        'anon': '100/hour',
        'user': '1000/hour'
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

# Redis Cache Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')

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
