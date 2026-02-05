"""
Client pour interroger TimescaleDB directement (sans ORM Django).
Gère les requêtes pour les données de séries temporelles.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from django.conf import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TimescaleDBClient:
    """Client pour se connecter et requêter TimescaleDB."""
    
    def __init__(self):
        """Initialise la connexion à TimescaleDB."""
        self.connection_params = settings.DATABASES['timescaledb']
        self.conn = None
    
    def get_connection(self):
        """Récupère ou crée une connexion à TimescaleDB."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(
                dbname=self.connection_params['NAME'],
                user=self.connection_params['USER'],
                password=self.connection_params['PASSWORD'],
                host=self.connection_params['HOST'],
                port=self.connection_params['PORT'],
                cursor_factory=RealDictCursor
            )
        return self.conn
    
    def close_connection(self):
        """Ferme la connexion."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None
    
    def execute_query(self, query, params=None):
        """
        Exécute une requête et retourne les résultats.
        
        Args:
            query: Requête SQL
            params: Paramètres de la requête
            
        Returns:
            Liste de dictionnaires avec les résultats
        """
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
            return results
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête: {e}")
            raise
    
    def get_sentiment_history(self, crypto_symbol, period='24h', start_date=None, end_date=None):
        """
        Récupère l'historique du sentiment pour une crypto.
        
        Args:
            crypto_symbol: Symbole de la crypto (ex: BTC, ETH)
            period: Période (24h, 7d, 30d) ou None si dates spécifiées
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
            
        Returns:
            Liste de données de sentiment
        """
        query = """
            SELECT 
                timestamp,
                crypto_symbol,
                sentiment_score,
                sentiment_label,
                source,
                confidence
            FROM sentiment_data
            WHERE LOWER(crypto_symbol) = LOWER(%s)
        """
        
        params = [crypto_symbol]
        
        if start_date and end_date:
            query += " AND timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif period:
            # Convertir la période en timedelta
            period_map = {
                '1h': timedelta(hours=1),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            delta = period_map.get(period, timedelta(hours=24))
            start_time = datetime.utcnow() - delta
            query += " AND timestamp >= %s"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC LIMIT 1000"
        
        return self.execute_query(query, params)
    
    def get_prediction_history(self, crypto_symbol, period='24h', start_date=None, end_date=None):
        """
        Récupère l'historique des prédictions pour une crypto.
        
        Args:
            crypto_symbol: Symbole de la crypto
            period: Période ou None si dates spécifiées
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel)
            
        Returns:
            Liste de données de prédiction
        """
        query = """
            SELECT 
                timestamp,
                crypto_symbol,
                predicted_price,
                actual_price,
                model_name,
                confidence_interval_low,
                confidence_interval_high
            FROM prediction_data
            WHERE LOWER(crypto_symbol) = LOWER(%s)
        """
        
        params = [crypto_symbol]
        
        if start_date and end_date:
            query += " AND timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif period:
            period_map = {
                '1h': timedelta(hours=1),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            delta = period_map.get(period, timedelta(hours=24))
            start_time = datetime.utcnow() - delta
            query += " AND timestamp >= %s"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC LIMIT 1000"
        
        return self.execute_query(query, params)
    
    def get_ticker_history(self, pair=None, period='24h', start_date=None, end_date=None):
        """Récupère l'historique des tickers."""
        query = """
            SELECT 
                timestamp,
                pair,
                last,
                bid,
                ask,
                volume_24h
            FROM ticker_data
            WHERE 1=1
        """
        
        params = []
        
        if pair:
            query += " AND UPPER(pair) = UPPER(%s)"
            params.append(pair)
        
        if start_date and end_date:
            query += " AND timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif period:
            period_map = {
                '1h': timedelta(hours=1),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            delta = period_map.get(period, timedelta(hours=24))
            start_time = datetime.utcnow() - delta
            query += " AND timestamp >= %s"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC LIMIT 1000"
        
        return self.execute_query(query, params)
    
    def get_trade_history(self, pair=None, period='24h', start_date=None, end_date=None):
        """Récupère l'historique des trades."""
        query = """
            SELECT 
                timestamp,
                pair,
                price,
                volume,
                side
            FROM trade_data
            WHERE 1=1
        """
        
        params = []
        
        if pair:
            query += " AND UPPER(pair) = UPPER(%s)"
            params.append(pair)
        
        if start_date and end_date:
            query += " AND timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif period:
            period_map = {
                '1h': timedelta(hours=1),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            delta = period_map.get(period, timedelta(hours=24))
            start_time = datetime.utcnow() - delta
            query += " AND timestamp >= %s"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC LIMIT 5000"
        
        return self.execute_query(query, params)
    
    def get_article_history(self, crypto_symbol=None, period='24h', start_date=None, end_date=None):
        """Récupère l'historique des articles."""
        query = """
            SELECT 
                timestamp,
                article_id,
                title,
                url,
                website,
                summary,
                cryptocurrencies_mentioned,
                sentiment_score,
                sentiment_label
            FROM article_data
            WHERE 1=1
        """
        
        params = []
        
        if crypto_symbol:
            query += " AND LOWER(%s) = ANY(ARRAY(SELECT LOWER(x) FROM unnest(cryptocurrencies_mentioned) AS x))"
            params.append(crypto_symbol)
        
        if start_date and end_date:
            query += " AND timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif period:
            period_map = {
                '1h': timedelta(hours=1),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            delta = period_map.get(period, timedelta(hours=24))
            start_time = datetime.utcnow() - delta
            query += " AND timestamp >= %s"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC LIMIT 100"
        
        return self.execute_query(query, params)
    
    def get_alert_history(self, pair=None, period='24h', start_date=None, end_date=None):
        """Récupère l'historique des alertes."""
        query = """
            SELECT 
                timestamp,
                pair,
                last_price,
                change_percent,
                threshold,
                alert_type
            FROM alert_data
            WHERE 1=1
        """
        
        params = []
        
        if pair:
            query += " AND pair = %s"
            params.append(pair)
        
        if start_date and end_date:
            query += " AND timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif period:
            period_map = {
                '1h': timedelta(hours=1),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            delta = period_map.get(period, timedelta(hours=24))
            start_time = datetime.utcnow() - delta
            query += " AND timestamp >= %s"
            params.append(start_time)
        
        query += " ORDER BY timestamp DESC LIMIT 500"
        
        return self.execute_query(query, params)

    def get_available_cryptos(self):
        """
        Récupère la liste de toutes les cryptos disponibles dans la base.
        Combine les données de ticker, sentiment et prediction.
        """
        query = """
            SELECT DISTINCT 'ticker' as data_type, pair as symbol, 
                   COUNT(*) as count, MAX(timestamp) as last_update
            FROM ticker_data
            GROUP BY pair
            UNION ALL
            SELECT DISTINCT 'trade' as data_type, pair as symbol,
                   COUNT(*) as count, MAX(timestamp) as last_update
            FROM trade_data
            GROUP BY pair
            UNION ALL
            SELECT DISTINCT 'sentiment' as data_type, crypto_symbol as symbol,
                   COUNT(*) as count, MAX(timestamp) as last_update
            FROM sentiment_data
            GROUP BY crypto_symbol
            UNION ALL
            SELECT DISTINCT 'prediction' as data_type, crypto_symbol as symbol,
                   COUNT(*) as count, MAX(timestamp) as last_update
            FROM prediction_data
            GROUP BY crypto_symbol
            ORDER BY data_type, symbol
        """
        return self.execute_query(query)

    def get_trading_pairs(self):
        """Récupère la liste des paires de trading disponibles."""
        query = """
            SELECT DISTINCT pair, 
                   COUNT(*) as ticker_count,
                   MAX(timestamp) as last_update
            FROM ticker_data
            GROUP BY pair
            ORDER BY pair
        """
        return self.execute_query(query)


# Instance globale du client
timescale_client = TimescaleDBClient()
