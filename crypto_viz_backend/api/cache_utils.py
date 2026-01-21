"""
Utilitaires pour le cache Redis dans l'API Django.
"""
from functools import wraps
from django.core.cache import cache
from django.conf import settings
import hashlib
import json


def cache_response(timeout=300, key_prefix='view'):
    """
    Décorateur pour mettre en cache les réponses des vues.
    
    Args:
        timeout: Durée du cache en secondes (défaut: 5 minutes)
        key_prefix: Préfixe pour la clé de cache
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Construire la clé de cache basée sur la requête
            cache_key_parts = [
                key_prefix,
                request.path,
                request.method,
                str(sorted(request.GET.items())),
            ]
            cache_key = hashlib.md5(
                ':'.join(cache_key_parts).encode()
            ).hexdigest()
            
            # Essayer de récupérer depuis le cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Sinon, appeler la vue et mettre en cache
            response = view_func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def cache_queryset(timeout=300, key_prefix='queryset'):
    """
    Décorateur pour mettre en cache les résultats de requêtes.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Créer une clé unique basée sur les arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = hashlib.md5(
                ':'.join(key_parts).encode()
            ).hexdigest()
            
            # Vérifier le cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Exécuter et mettre en cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalide toutes les clés de cache correspondant à un pattern.
    
    Args:
        pattern: Pattern de clé (ex: 'ticker:*')
    """
    from django_redis import get_redis_connection
    
    try:
        redis_conn = get_redis_connection("default")
        # Utiliser SCAN pour éviter de bloquer Redis
        cursor = 0
        while True:
            cursor, keys = redis_conn.scan(
                cursor=cursor,
                match=f"{settings.CACHES['default']['KEY_PREFIX']}:{pattern}",
                count=100
            )
            if keys:
                redis_conn.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        # Log l'erreur mais ne pas faire crasher
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")


def get_cache_stats():
    """
    Récupère les statistiques du cache Redis.
    """
    from django_redis import get_redis_connection
    
    try:
        redis_conn = get_redis_connection("default")
        info = redis_conn.info()
        
        return {
            'connected_clients': info.get('connected_clients', 0),
            'used_memory': info.get('used_memory_human', '0'),
            'total_commands_processed': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'hit_rate': round(
                info.get('keyspace_hits', 0) / 
                max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
                2
            )
        }
    except Exception as e:
        return {'error': str(e)}


# Durées de cache recommandées pour différents types de données
CACHE_TIMEOUTS = {
    'ticker_realtime': 5,           # 5 secondes pour les prix en temps réel
    'ticker_minute': 60,            # 1 minute pour les agrégations minute
    'ticker_hour': 3600,            # 1 heure pour les agrégations horaires
    'articles_latest': 300,         # 5 minutes pour les derniers articles
    'crypto_list': 3600,            # 1 heure pour la liste des cryptos
    'analytics': 300,               # 5 minutes pour les analytics
    'predictions': 600,             # 10 minutes pour les prédictions
    'config': 86400,                # 24 heures pour les configurations
}
