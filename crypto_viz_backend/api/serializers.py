"""
Serializers pour les APIs REST CRYPTO VIZ.
Définit les structures de données pour la sérialisation/désérialisation JSON.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from .models import CryptoConfiguration, VisualizationParameter


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Bitcoin Configuration',
            summary='Configuration pour Bitcoin',
            description='Exemple de configuration de crypto-monnaie active',
            value={
                'id': 1,
                'symbol': 'BTC',
                'name': 'Bitcoin',
                'is_active': True,
                'created_at': '2024-01-15T10:30:00.000000Z',
                'updated_at': '2024-01-15T10:30:00.000000Z'
            },
            response_only=True,
        ),
        OpenApiExample(
            'Ethereum Configuration',
            summary='Configuration pour Ethereum',
            value={
                'id': 2,
                'symbol': 'ETH',
                'name': 'Ethereum',
                'is_active': True,
                'created_at': '2024-01-15T10:31:00.000000Z',
                'updated_at': '2024-01-15T10:31:00.000000Z'
            },
            response_only=True,
        ),
    ]
)
class CryptoConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer pour la configuration des crypto-monnaies suivies.
    
    Permet de gérer la liste des crypto-monnaies actives dans le système.
    """
    class Meta:
        model = CryptoConfiguration
        fields = ['id', 'symbol', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'symbol': {
                'help_text': 'Symbole de la crypto-monnaie (ex: BTC, ETH, SOL)'
            },
            'name': {
                'help_text': 'Nom complet de la crypto-monnaie (ex: Bitcoin, Ethereum)'
            },
            'is_active': {
                'help_text': 'Indique si la crypto est activement suivie'
            },
        }


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Dashboard BTC',
            summary='Configuration de visualisation pour BTC',
            value={
                'id': 1,
                'name': 'Mon Dashboard BTC',
                'crypto_symbol': 'BTC',
                'time_range': '24h',
                'chart_type': 'candlestick',
                'indicators': ['SMA_20', 'RSI', 'MACD'],
                'created_at': '2024-01-15T10:30:00.000000Z',
                'updated_at': '2024-01-15T10:30:00.000000Z'
            },
            response_only=True,
        ),
    ]
)
class VisualizationParameterSerializer(serializers.ModelSerializer):
    """
    Serializer pour les paramètres de visualisation sauvegardés.
    
    Permet aux utilisateurs de sauvegarder leurs configurations de graphiques
    préférées pour un accès rapide.
    """
    class Meta:
        model = VisualizationParameter
        fields = ['id', 'name', 'crypto_symbol', 'time_range', 'chart_type', 
                  'indicators', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {
                'help_text': 'Nom de la configuration (ex: "Mon Dashboard BTC")'
            },
            'crypto_symbol': {
                'help_text': 'Symbole de la crypto associée (ex: BTC, ETH)'
            },
            'time_range': {
                'help_text': 'Plage temporelle (valeurs: 1h, 24h, 7d, 30d)'
            },
            'chart_type': {
                'help_text': 'Type de graphique (valeurs: candlestick, line, area, bar)'
            },
            'indicators': {
                'help_text': 'Liste des indicateurs techniques (ex: ["SMA_20", "RSI", "MACD"])'
            },
        }


# =============================================================================
# Serializers pour données TimescaleDB (sans modèles Django)
# =============================================================================

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Sentiment Positif BTC',
            summary='Exemple de sentiment positif pour Bitcoin',
            description='Données de sentiment agrégées à partir des articles de presse',
            value={
                'timestamp': '2024-01-15T14:30:00.000000Z',
                'crypto_symbol': 'BTC',
                'sentiment_score': 0.85,
                'sentiment_label': 'positive',
                'source': 'aggregated_articles',
                'confidence': 0.92
            },
            response_only=True,
        ),
        OpenApiExample(
            'Sentiment Négatif ETH',
            summary='Exemple de sentiment négatif pour Ethereum',
            value={
                'timestamp': '2024-01-15T14:25:00.000000Z',
                'crypto_symbol': 'ETH',
                'sentiment_score': 0.25,
                'sentiment_label': 'negative',
                'source': 'aggregated_articles',
                'confidence': 0.78
            },
            response_only=True,
        ),
    ]
)
class SentimentDataSerializer(serializers.Serializer):
    """
    Serializer pour les données de sentiment depuis TimescaleDB.
    
    Le sentiment est calculé à partir de l'analyse NLP des articles de presse crypto.
    Les scores vont de 0.0 (très négatif) à 1.0 (très positif).
    """
    timestamp = serializers.DateTimeField(
        help_text='Horodatage de la mesure de sentiment (format ISO 8601 UTC)'
    )
    crypto_symbol = serializers.CharField(
        max_length=50,
        help_text='Symbole de la crypto-monnaie (ex: BTC, ETH, SOL)'
    )
    sentiment_score = serializers.FloatField(
        help_text='Score de sentiment entre 0.0 (négatif) et 1.0 (positif)'
    )
    sentiment_label = serializers.CharField(
        max_length=20,
        help_text='Label de sentiment: "positive", "negative", ou "neutral"'
    )
    source = serializers.CharField(
        max_length=100,
        help_text='Source des données (ex: "aggregated_articles", "twitter")'
    )
    confidence = serializers.FloatField(
        help_text='Niveau de confiance de l\'analyse (0.0 à 1.0)'
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Prédiction BTC',
            summary='Prédiction de prix pour Bitcoin',
            description='Prédiction générée par le modèle de moyenne mobile',
            value={
                'timestamp': '2024-01-15T15:00:00.000000Z',
                'crypto_symbol': 'BTC',
                'predicted_price': 43250.75,
                'actual_price': 43180.50,
                'model_name': 'moving_average',
                'confidence_interval_low': 42800.00,
                'confidence_interval_high': 43700.00
            },
            response_only=True,
        ),
    ]
)
class PredictionDataSerializer(serializers.Serializer):
    """
    Serializer pour les données de prédiction de prix depuis TimescaleDB.
    
    Les prédictions sont générées par des modèles ML (actuellement moyenne mobile).
    Inclut des intervalles de confiance pour évaluer l'incertitude.
    """
    timestamp = serializers.DateTimeField(
        help_text='Horodatage de la prédiction (format ISO 8601 UTC)'
    )
    crypto_symbol = serializers.CharField(
        max_length=10,
        help_text='Symbole de la crypto-monnaie (ex: BTC, ETH)'
    )
    predicted_price = serializers.FloatField(
        help_text='Prix prédit en USD'
    )
    actual_price = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text='Prix réel observé en USD (disponible après coup pour comparaison)'
    )
    model_name = serializers.CharField(
        max_length=50,
        help_text='Nom du modèle utilisé (ex: "moving_average", "lstm", "arima")'
    )
    confidence_interval_low = serializers.FloatField(
        help_text='Borne inférieure de l\'intervalle de confiance en USD'
    )
    confidence_interval_high = serializers.FloatField(
        help_text='Borne supérieure de l\'intervalle de confiance en USD'
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Ticker BTC/USD',
            summary='Prix temps réel Bitcoin',
            description='Données de ticker pour la paire BTC/USD',
            value={
                'timestamp': '2024-01-15T15:30:45.123456Z',
                'pair': 'XBT/USD',
                'last': 43250.50,
                'bid': 43248.00,
                'ask': 43252.00,
                'volume_24h': 15234.567
            },
            response_only=True,
        ),
        OpenApiExample(
            'Ticker ETH/USD',
            summary='Prix temps réel Ethereum',
            value={
                'timestamp': '2024-01-15T15:30:45.234567Z',
                'pair': 'ETH/USD',
                'last': 2650.25,
                'bid': 2649.50,
                'ask': 2651.00,
                'volume_24h': 125678.90
            },
            response_only=True,
        ),
    ]
)
class TickerDataSerializer(serializers.Serializer):
    """
    Serializer pour les données de ticker (prix temps réel) depuis TimescaleDB.
    
    Les tickers représentent l'état actuel du marché pour une paire de trading.
    Les données proviennent de l'API Kraken en temps réel.
    """
    timestamp = serializers.DateTimeField(
        help_text='Horodatage du ticker (format ISO 8601 UTC)'
    )
    pair = serializers.CharField(
        max_length=20,
        help_text='Paire de trading (ex: "XBT/USD", "ETH/USD"). Note: Kraken utilise XBT pour Bitcoin'
    )
    last = serializers.FloatField(
        help_text='Dernier prix de transaction en USD'
    )
    bid = serializers.FloatField(
        help_text='Meilleure offre d\'achat (prix que les acheteurs sont prêts à payer)'
    )
    ask = serializers.FloatField(
        help_text='Meilleure offre de vente (prix que les vendeurs demandent)'
    )
    volume_24h = serializers.FloatField(
        help_text='Volume total échangé sur les dernières 24 heures (en crypto)'
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Trade Achat BTC',
            summary='Transaction d\'achat Bitcoin',
            value={
                'timestamp': '2024-01-15T15:30:45.123456Z',
                'pair': 'XBT/USD',
                'price': 43250.50,
                'volume': 0.5,
                'side': 'b'
            },
            response_only=True,
        ),
        OpenApiExample(
            'Trade Vente ETH',
            summary='Transaction de vente Ethereum',
            value={
                'timestamp': '2024-01-15T15:30:46.234567Z',
                'pair': 'ETH/USD',
                'price': 2650.25,
                'volume': 2.5,
                'side': 's'
            },
            response_only=True,
        ),
    ]
)
class TradeDataSerializer(serializers.Serializer):
    """
    Serializer pour les données de trade (transactions) depuis TimescaleDB.
    
    Chaque trade représente une transaction individuelle exécutée sur le marché.
    """
    timestamp = serializers.DateTimeField(
        help_text='Horodatage de la transaction (format ISO 8601 UTC)'
    )
    pair = serializers.CharField(
        max_length=20,
        help_text='Paire de trading (ex: "XBT/USD", "ETH/USD")'
    )
    price = serializers.FloatField(
        help_text='Prix de la transaction en USD'
    )
    volume = serializers.FloatField(
        help_text='Volume échangé (quantité de crypto)'
    )
    side = serializers.CharField(
        max_length=1,
        help_text='Côté de la transaction: "b" = buy (achat), "s" = sell (vente)'
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Article Positif BTC',
            summary='Article avec sentiment positif sur Bitcoin',
            description='Article de CoinTelegraph analysé automatiquement',
            value={
                'timestamp': '2024-01-15T14:00:00.000000Z',
                'article_id': 'cointelegraph_1705326000',
                'title': 'Bitcoin atteint un nouveau sommet mensuel alors que l\'adoption institutionnelle s\'accélère',
                'url': 'https://cointelegraph.com/news/bitcoin-monthly-high',
                'website': 'cointelegraph.com',
                'summary': 'Le prix du Bitcoin a franchi la barre des 43 000$ suite à des annonces positives...',
                'cryptocurrencies_mentioned': ['BTC', 'ETH'],
                'sentiment_score': 0.89,
                'sentiment_label': 'positive'
            },
            response_only=True,
        ),
    ]
)
class ArticleDataSerializer(serializers.Serializer):
    """
    Serializer pour les données d'articles depuis TimescaleDB.
    
    Les articles sont collectés automatiquement depuis des sites crypto spécialisés
    et analysés pour extraire le sentiment et les cryptos mentionnées.
    """
    timestamp = serializers.DateTimeField(
        help_text='Horodatage de collecte de l\'article (format ISO 8601 UTC)'
    )
    article_id = serializers.CharField(
        max_length=255,
        help_text='Identifiant unique de l\'article (format: source_timestamp)'
    )
    title = serializers.CharField(
        help_text='Titre de l\'article'
    )
    url = serializers.URLField(
        help_text='URL complète de l\'article source'
    )
    website = serializers.CharField(
        max_length=100,
        help_text='Nom de domaine du site source (ex: "cointelegraph.com")'
    )
    summary = serializers.CharField(
        help_text='Résumé ou extrait du contenu de l\'article'
    )
    cryptocurrencies_mentioned = serializers.ListField(
        child=serializers.CharField(),
        help_text='Liste des symboles de crypto-monnaies mentionnées (ex: ["BTC", "ETH"])'
    )
    sentiment_score = serializers.FloatField(
        help_text='Score de sentiment de l\'article (0.0 à 1.0)'
    )
    sentiment_label = serializers.CharField(
        max_length=20,
        help_text='Label de sentiment: "positive", "negative", ou "neutral"'
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Alerte Hausse BTC',
            summary='Alerte de hausse de prix Bitcoin',
            description='Alerte générée suite à une hausse > 1%',
            value={
                'timestamp': '2024-01-15T15:45:00.000000Z',
                'pair': 'XBT/USD',
                'last_price': 43500.00,
                'change_percent': 1.5,
                'threshold': 1.0,
                'alert_type': 'PRICE_UP'
            },
            response_only=True,
        ),
        OpenApiExample(
            'Alerte Baisse ETH',
            summary='Alerte de baisse de prix Ethereum',
            value={
                'timestamp': '2024-01-15T15:50:00.000000Z',
                'pair': 'ETH/USD',
                'last_price': 2580.00,
                'change_percent': -2.1,
                'threshold': 1.0,
                'alert_type': 'PRICE_DOWN'
            },
            response_only=True,
        ),
    ]
)
class AlertDataSerializer(serializers.Serializer):
    """
    Serializer pour les données d'alertes depuis TimescaleDB.
    
    Les alertes sont générées automatiquement lorsque le prix d'une crypto
    varie de plus d'un certain seuil (par défaut 1%).
    """
    timestamp = serializers.DateTimeField(
        help_text='Horodatage de l\'alerte (format ISO 8601 UTC)'
    )
    pair = serializers.CharField(
        max_length=20,
        help_text='Paire de trading concernée (ex: "XBT/USD")'
    )
    last_price = serializers.FloatField(
        help_text='Prix au moment de l\'alerte en USD'
    )
    change_percent = serializers.FloatField(
        help_text='Pourcentage de variation (positif = hausse, négatif = baisse)'
    )
    threshold = serializers.FloatField(
        help_text='Seuil de déclenchement de l\'alerte (en %)'
    )
    alert_type = serializers.CharField(
        max_length=20,
        help_text='Type d\'alerte: "PRICE_UP" (hausse) ou "PRICE_DOWN" (baisse)'
    )


# =============================================================================
# Serializers pour les réponses API
# =============================================================================

class SentimentHistoryResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse de l'endpoint historique sentiment."""
    crypto_symbol = serializers.CharField(help_text='Symbole de la crypto demandée')
    count = serializers.IntegerField(help_text='Nombre de résultats retournés')
    data = SentimentDataSerializer(many=True, help_text='Liste des données de sentiment')


class PredictionHistoryResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse de l'endpoint historique prédictions."""
    crypto_symbol = serializers.CharField(help_text='Symbole de la crypto demandée')
    count = serializers.IntegerField(help_text='Nombre de résultats retournés')
    data = PredictionDataSerializer(many=True, help_text='Liste des prédictions')


class TickerHistoryResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse de l'endpoint historique tickers."""
    pair = serializers.CharField(help_text='Paire de trading demandée')
    count = serializers.IntegerField(help_text='Nombre de résultats retournés')
    data = TickerDataSerializer(many=True, help_text='Liste des données de ticker')


class TradeHistoryResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse de l'endpoint historique trades."""
    pair = serializers.CharField(help_text='Paire de trading demandée')
    count = serializers.IntegerField(help_text='Nombre de résultats retournés')
    data = TradeDataSerializer(many=True, help_text='Liste des transactions')


class ArticleHistoryResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse de l'endpoint historique articles."""
    crypto_symbol = serializers.CharField(help_text='Symbole de la crypto filtrée ou "ALL"')
    count = serializers.IntegerField(help_text='Nombre de résultats retournés')
    data = ArticleDataSerializer(many=True, help_text='Liste des articles')


class AlertHistoryResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse de l'endpoint historique alertes."""
    pair = serializers.CharField(help_text='Paire de trading filtrée ou "ALL"')
    count = serializers.IntegerField(help_text='Nombre de résultats retournés')
    data = AlertDataSerializer(many=True, help_text='Liste des alertes')


class HealthCheckResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse du health check."""
    status = serializers.CharField(help_text='État du service: "healthy" ou "unhealthy"')
    service = serializers.CharField(help_text='Nom du service')
    version = serializers.CharField(help_text='Version de l\'API')


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer pour les réponses d'erreur."""
    error = serializers.CharField(help_text='Message d\'erreur détaillé')
