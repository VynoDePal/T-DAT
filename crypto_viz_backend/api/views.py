"""
Vues API REST pour CRYPTO VIZ.
Fournit les endpoints pour accéder aux données historiques depuis TimescaleDB.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.dateparse import parse_datetime
import logging

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
    OpenApiTypes,
)

from .models import CryptoConfiguration, VisualizationParameter
from .serializers import (
    CryptoConfigurationSerializer,
    VisualizationParameterSerializer,
    SentimentDataSerializer,
    PredictionDataSerializer,
    TickerDataSerializer,
    TradeDataSerializer,
    ArticleDataSerializer,
    AlertDataSerializer,
    SentimentHistoryResponseSerializer,
    PredictionHistoryResponseSerializer,
    TickerHistoryResponseSerializer,
    TradeHistoryResponseSerializer,
    ArticleHistoryResponseSerializer,
    AlertHistoryResponseSerializer,
    HealthCheckResponseSerializer,
    ErrorResponseSerializer,
)
from .timescale_client import timescale_client

logger = logging.getLogger(__name__)


# =============================================================================
# Paramètres OpenAPI réutilisables
# =============================================================================

PERIOD_PARAMETER = OpenApiParameter(
    name='periode',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=False,
    description='''Période de temps pour filtrer les données.

**Valeurs acceptées:**
- `1h` : Dernière heure
- `24h` : Dernières 24 heures (défaut)
- `7d` : 7 derniers jours
- `30d` : 30 derniers jours

⚠️ Si `date_debut` et `date_fin` sont fournis, ce paramètre est ignoré.''',
    enum=['1h', '24h', '7d', '30d'],
    default='24h',
    examples=[
        OpenApiExample('Dernière heure', value='1h'),
        OpenApiExample('24 heures', value='24h'),
        OpenApiExample('7 jours', value='7d'),
        OpenApiExample('30 jours', value='30d'),
    ]
)

DATE_DEBUT_PARAMETER = OpenApiParameter(
    name='date_debut',
    type=OpenApiTypes.DATETIME,
    location=OpenApiParameter.QUERY,
    required=False,
    description='''Date de début pour filtrer les données (format ISO 8601).

**Format:** `YYYY-MM-DDTHH:MM:SSZ` ou `YYYY-MM-DDTHH:MM:SS+HH:MM`

**Exemples:**
- `2024-01-15T00:00:00Z`
- `2024-01-15T10:30:00+01:00`

⚠️ Doit être utilisé avec `date_fin`. Si fourni, le paramètre `periode` est ignoré.''',
    examples=[
        OpenApiExample('Début janvier 2024', value='2024-01-01T00:00:00Z'),
        OpenApiExample('15 janvier 2024 10h30', value='2024-01-15T10:30:00Z'),
    ]
)

DATE_FIN_PARAMETER = OpenApiParameter(
    name='date_fin',
    type=OpenApiTypes.DATETIME,
    location=OpenApiParameter.QUERY,
    required=False,
    description='''Date de fin pour filtrer les données (format ISO 8601).

**Format:** `YYYY-MM-DDTHH:MM:SSZ` ou `YYYY-MM-DDTHH:MM:SS+HH:MM`

⚠️ Doit être utilisé avec `date_debut`. Si fourni, le paramètre `periode` est ignoré.''',
    examples=[
        OpenApiExample('Fin janvier 2024', value='2024-01-31T23:59:59Z'),
        OpenApiExample('15 janvier 2024 18h00', value='2024-01-15T18:00:00Z'),
    ]
)


@extend_schema_view(
    list=extend_schema(
        tags=['Configuration'],
        summary='Lister toutes les crypto-monnaies configurées',
        description='''
Retourne la liste de toutes les crypto-monnaies configurées dans le système.

**Utilisation Frontend:**
- Afficher la liste des cryptos disponibles dans un sélecteur
- Filtrer les cryptos actives pour les graphiques
- Gérer les préférences utilisateur
        ''',
        responses={200: CryptoConfigurationSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=['Configuration'],
        summary='Récupérer une crypto-monnaie par ID',
        description='Retourne les détails d\'une crypto-monnaie spécifique.',
        responses={
            200: CryptoConfigurationSerializer,
            404: ErrorResponseSerializer,
        },
    ),
    create=extend_schema(
        tags=['Configuration'],
        summary='Ajouter une nouvelle crypto-monnaie',
        description='''
Ajoute une nouvelle crypto-monnaie à suivre dans le système.

**Champs requis:**
- `symbol`: Symbole unique (ex: BTC, ETH)
- `name`: Nom complet de la crypto

**Exemple de payload:**
```json
{
    "symbol": "SOL",
    "name": "Solana",
    "is_active": true
}
```
        ''',
        responses={
            201: CryptoConfigurationSerializer,
            400: ErrorResponseSerializer,
        },
    ),
    update=extend_schema(
        tags=['Configuration'],
        summary='Mettre à jour une crypto-monnaie',
        description='Met à jour tous les champs d\'une crypto-monnaie existante.',
        responses={
            200: CryptoConfigurationSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    ),
    partial_update=extend_schema(
        tags=['Configuration'],
        summary='Mettre à jour partiellement une crypto-monnaie',
        description='Met à jour uniquement les champs fournis.',
        responses={
            200: CryptoConfigurationSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    ),
    destroy=extend_schema(
        tags=['Configuration'],
        summary='Supprimer une crypto-monnaie',
        description='Supprime une crypto-monnaie de la configuration.',
        responses={
            204: None,
            404: ErrorResponseSerializer,
        },
    ),
)
class CryptoConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des crypto-monnaies configurées.
    
    Permet de gérer la liste des crypto-monnaies suivies par le système.
    Ces données sont stockées dans SQLite (métadonnées).
    """
    queryset = CryptoConfiguration.objects.all()
    serializer_class = CryptoConfigurationSerializer


@extend_schema_view(
    list=extend_schema(
        tags=['Configuration'],
        summary='Lister les configurations de visualisation',
        description='''
Retourne les configurations de visualisation sauvegardées.

**Utilisation Frontend:**
- Charger les dashboards sauvegardés
- Restaurer les préférences utilisateur
- Afficher la liste des configurations disponibles

**Note:** Si l'utilisateur est authentifié, seules ses configurations sont retournées.
        ''',
        responses={200: VisualizationParameterSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=['Configuration'],
        summary='Récupérer une configuration par ID',
        description='Retourne les détails d\'une configuration de visualisation.',
        responses={
            200: VisualizationParameterSerializer,
            404: ErrorResponseSerializer,
        },
    ),
    create=extend_schema(
        tags=['Configuration'],
        summary='Créer une configuration de visualisation',
        description='''
Sauvegarde une nouvelle configuration de visualisation.

**Champs requis:**
- `name`: Nom de la configuration
- `crypto_symbol`: Symbole de la crypto
- `time_range`: Plage temporelle
- `chart_type`: Type de graphique

**Exemple de payload:**
```json
{
    "name": "Mon Dashboard BTC",
    "crypto_symbol": "BTC",
    "time_range": "24h",
    "chart_type": "candlestick",
    "indicators": ["SMA_20", "RSI", "MACD"]
}
```

**Types de graphiques supportés:**
- `candlestick`: Chandeliers japonais
- `line`: Courbe simple
- `area`: Graphique en aire
- `bar`: Barres verticales

**Indicateurs techniques disponibles:**
- `SMA_20`, `SMA_50`, `SMA_200`: Moyennes mobiles simples
- `EMA_12`, `EMA_26`: Moyennes mobiles exponentielles
- `RSI`: Relative Strength Index
- `MACD`: Moving Average Convergence Divergence
- `BOLLINGER`: Bandes de Bollinger
        ''',
        responses={
            201: VisualizationParameterSerializer,
            400: ErrorResponseSerializer,
        },
    ),
    update=extend_schema(
        tags=['Configuration'],
        summary='Mettre à jour une configuration',
        description='Met à jour tous les champs d\'une configuration existante.',
        responses={
            200: VisualizationParameterSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    ),
    partial_update=extend_schema(
        tags=['Configuration'],
        summary='Mettre à jour partiellement une configuration',
        description='Met à jour uniquement les champs fournis.',
        responses={
            200: VisualizationParameterSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    ),
    destroy=extend_schema(
        tags=['Configuration'],
        summary='Supprimer une configuration',
        description='Supprime une configuration de visualisation.',
        responses={
            204: None,
            404: ErrorResponseSerializer,
        },
    ),
)
class VisualizationParameterViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les paramètres de visualisation sauvegardés.
    
    Permet aux utilisateurs de sauvegarder et charger leurs configurations
    de graphiques préférées.
    """
    queryset = VisualizationParameter.objects.all()
    serializer_class = VisualizationParameterSerializer
    
    def get_queryset(self):
        """Filtre par utilisateur si authentifié."""
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
        return queryset


class SentimentHistoryView(APIView):
    """
    API pour récupérer l'historique du sentiment.
    Endpoint: /api/v1/sentiment/{crypto_symbol}/historique
    """
    
    @extend_schema(
        tags=['Sentiment'],
        operation_id='getSentimentHistory',
        summary='Récupérer l\'historique du sentiment pour une crypto',
        description='''
Retourne l'historique des données de sentiment pour une crypto-monnaie spécifique.

## Description

Le sentiment est calculé à partir de l'analyse NLP des articles de presse crypto.
Les données sont agrégées par fenêtres de 5 minutes par Apache Spark.

## Utilisation Frontend

```javascript
// Exemple avec fetch
const response = await fetch('/api/v1/sentiment/BTC/historique/?periode=24h');
const data = await response.json();

// Afficher dans un graphique
data.data.forEach(point => {
    chart.addPoint({
        x: new Date(point.timestamp),
        y: point.sentiment_score,
        label: point.sentiment_label
    });
});
```

## Interprétation des scores

| Score | Label | Signification |
|-------|-------|---------------|
| 0.0 - 0.4 | negative | Sentiment négatif (peur, incertitude) |
| 0.4 - 0.6 | neutral | Sentiment neutre |
| 0.6 - 1.0 | positive | Sentiment positif (optimisme, FOMO) |

## Limites

- Maximum 1000 résultats par requête
- Données disponibles sur 90 jours glissants
        ''',
        parameters=[
            OpenApiParameter(
                name='crypto_symbol',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                required=True,
                description='Symbole de la crypto-monnaie (ex: BTC, ETH, SOL)',
                examples=[
                    OpenApiExample('Bitcoin', value='BTC'),
                    OpenApiExample('Ethereum', value='ETH'),
                    OpenApiExample('Solana', value='SOL'),
                ]
            ),
            PERIOD_PARAMETER,
            DATE_DEBUT_PARAMETER,
            DATE_FIN_PARAMETER,
        ],
        responses={
            200: SentimentHistoryResponseSerializer,
            500: ErrorResponseSerializer,
        },
        examples=[
            OpenApiExample(
                'Réponse sentiment BTC',
                value={
                    'crypto_symbol': 'BTC',
                    'count': 2,
                    'data': [
                        {
                            'timestamp': '2024-01-15T14:30:00.000000Z',
                            'crypto_symbol': 'BTC',
                            'sentiment_score': 0.85,
                            'sentiment_label': 'positive',
                            'source': 'aggregated_articles',
                            'confidence': 0.92
                        },
                        {
                            'timestamp': '2024-01-15T14:25:00.000000Z',
                            'crypto_symbol': 'BTC',
                            'sentiment_score': 0.72,
                            'sentiment_label': 'positive',
                            'source': 'aggregated_articles',
                            'confidence': 0.88
                        }
                    ]
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request, crypto_symbol):
        """Récupère l'historique du sentiment pour une crypto."""
        try:
            period = request.query_params.get('periode', '24h')
            start_date = request.query_params.get('date_debut')
            end_date = request.query_params.get('date_fin')
            
            if start_date:
                start_date = parse_datetime(start_date)
            if end_date:
                end_date = parse_datetime(end_date)
            
            data = timescale_client.get_sentiment_history(
                crypto_symbol,
                period=period if not start_date else None,
                start_date=start_date,
                end_date=end_date
            )
            
            serializer = SentimentDataSerializer(data, many=True)
            
            return Response({
                'crypto_symbol': crypto_symbol.upper(),
                'count': len(data),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du sentiment: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PredictionHistoryView(APIView):
    """
    API pour récupérer l'historique des prédictions.
    Endpoint: /api/v1/prediction/{crypto_symbol}/historique
    """
    
    @extend_schema(
        tags=['Predictions'],
        operation_id='getPredictionHistory',
        summary='Récupérer l\'historique des prédictions de prix',
        description='''
Retourne l'historique des prédictions de prix pour une crypto-monnaie.

## Description

Les prédictions sont générées par des modèles ML basés sur l'analyse des tendances.
Actuellement, le modèle `moving_average` est utilisé (moyenne mobile avec écart-type).

## Utilisation Frontend

```javascript
// Récupérer les prédictions
const response = await fetch('/api/v1/prediction/BTC/historique/?periode=7d');
const data = await response.json();

// Afficher avec intervalles de confiance
data.data.forEach(point => {
    chart.addBand({
        from: point.confidence_interval_low,
        to: point.confidence_interval_high,
        color: 'rgba(100, 100, 255, 0.2)'
    });
    chart.addLine({
        x: new Date(point.timestamp),
        y: point.predicted_price,
        color: 'blue'
    });
});
```

## Modèles disponibles

| Modèle | Description | Précision estimée |
|--------|-------------|-------------------|
| `moving_average` | Moyenne mobile simple | ~60-70% |

## Intervalles de confiance

Les bornes `confidence_interval_low` et `confidence_interval_high` représentent
l'intervalle dans lequel le prix a ~68% de chances de se trouver (±1 écart-type).

## Limites

- Maximum 1000 résultats par requête
- Prédictions sur 90 jours glissants
        ''',
        parameters=[
            OpenApiParameter(
                name='crypto_symbol',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                required=True,
                description='Symbole de la crypto-monnaie',
                examples=[
                    OpenApiExample('Bitcoin', value='BTC'),
                    OpenApiExample('Ethereum', value='ETH'),
                ]
            ),
            PERIOD_PARAMETER,
            DATE_DEBUT_PARAMETER,
            DATE_FIN_PARAMETER,
        ],
        responses={
            200: PredictionHistoryResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request, crypto_symbol):
        """Récupère l'historique des prédictions pour une crypto."""
        try:
            period = request.query_params.get('periode', '24h')
            start_date = request.query_params.get('date_debut')
            end_date = request.query_params.get('date_fin')
            
            if start_date:
                start_date = parse_datetime(start_date)
            if end_date:
                end_date = parse_datetime(end_date)
            
            data = timescale_client.get_prediction_history(
                crypto_symbol,
                period=period if not start_date else None,
                start_date=start_date,
                end_date=end_date
            )
            
            serializer = PredictionDataSerializer(data, many=True)
            
            return Response({
                'crypto_symbol': crypto_symbol.upper(),
                'count': len(data),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des prédictions: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TickerHistoryView(APIView):
    """
    API pour récupérer l'historique des tickers (prix).
    Endpoint: /api/v1/ticker/{pair}/historique
    """
    
    @extend_schema(
        tags=['Tickers'],
        operation_id='getTickerHistory',
        summary='Récupérer l\'historique des prix pour une paire',
        description='''
Retourne l'historique des prix (tickers) pour une paire de trading.

## Description

Les tickers contiennent les prix en temps réel collectés depuis Kraken.
Chaque ticker inclut le dernier prix, le bid, l'ask et le volume 24h.

## Paires supportées

| Paire | Description |
|-------|-------------|
| `XBT/USD` | Bitcoin (Kraken utilise XBT) |
| `ETH/USD` | Ethereum |
| `SOL/USD` | Solana |
| `ADA/USD` | Cardano |
| `MATIC/USD` | Polygon |
| `DOT/USD` | Polkadot |
| `LINK/USD` | Chainlink |
| `USDT/USD` | Tether |

## Utilisation Frontend

```javascript
// Récupérer l'historique des prix
const response = await fetch('/api/v1/ticker/XBT/USD/historique/?periode=24h');
const data = await response.json();

// Créer un graphique candlestick
const ohlcData = processToOHLC(data.data, '1h'); // Agrégation horaire
chart.setData(ohlcData);
```

## Spread et Liquidité

Le spread (ask - bid) indique la liquidité du marché:
- **< 0.1%** : Très liquide
- **0.1% - 0.5%** : Normal
- **> 0.5%** : Faible liquidité

## Limites

- Maximum 1000 résultats par requête
- Données sur 90 jours glissants
        ''',
        parameters=[
            OpenApiParameter(
                name='pair',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                required=True,
                description='Paire de trading (ex: XBT/USD, ETH/USD). Note: utilisez XBT pour Bitcoin.',
                examples=[
                    OpenApiExample('Bitcoin', value='XBT/USD'),
                    OpenApiExample('Ethereum', value='ETH/USD'),
                    OpenApiExample('Solana', value='SOL/USD'),
                ]
            ),
            PERIOD_PARAMETER,
            DATE_DEBUT_PARAMETER,
            DATE_FIN_PARAMETER,
        ],
        responses={
            200: TickerHistoryResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request, pair):
        """Récupère l'historique des tickers pour une paire."""
        try:
            period = request.query_params.get('periode', '24h')
            start_date = request.query_params.get('date_debut')
            end_date = request.query_params.get('date_fin')
            
            if start_date:
                start_date = parse_datetime(start_date)
            if end_date:
                end_date = parse_datetime(end_date)
            
            data = timescale_client.get_ticker_history(
                pair,
                period=period if not start_date else None,
                start_date=start_date,
                end_date=end_date
            )
            
            serializer = TickerDataSerializer(data, many=True)
            
            return Response({
                'pair': pair.upper(),
                'count': len(data),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tickers: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TradeHistoryView(APIView):
    """
    API pour récupérer l'historique des trades.
    Endpoint: /api/v1/trade/{pair}/historique
    """
    
    @extend_schema(
        tags=['Trades'],
        operation_id='getTradeHistory',
        summary='Récupérer l\'historique des transactions',
        description='''
Retourne l'historique des transactions (trades) pour une paire de trading.

## Description

Chaque trade représente une transaction individuelle exécutée sur Kraken.
Les données incluent le prix, le volume et le côté (achat/vente).

## Utilisation Frontend

```javascript
// Récupérer les trades récents
const response = await fetch('/api/v1/trade/XBT/USD/historique/?periode=1h');
const data = await response.json();

// Calculer le ratio buy/sell
const buys = data.data.filter(t => t.side === 'b');
const sells = data.data.filter(t => t.side === 's');
const ratio = buys.length / sells.length;

// Afficher dans un graphique de volume
data.data.forEach(trade => {
    volumeChart.addBar({
        x: new Date(trade.timestamp),
        y: trade.volume,
        color: trade.side === 'b' ? 'green' : 'red'
    });
});
```

## Analyse des trades

| Indicateur | Calcul | Interprétation |
|------------|--------|----------------|
| Buy/Sell Ratio | buys / sells | > 1 = pression acheteuse |
| Volume moyen | sum(volume) / count | Liquidité |
| Price Impact | max - min | Volatilité |

## Limites

- Maximum 5000 résultats par requête
- Données sur 90 jours glissants
        ''',
        parameters=[
            OpenApiParameter(
                name='pair',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                required=True,
                description='Paire de trading (ex: XBT/USD, ETH/USD)',
                examples=[
                    OpenApiExample('Bitcoin', value='XBT/USD'),
                    OpenApiExample('Ethereum', value='ETH/USD'),
                ]
            ),
            PERIOD_PARAMETER,
            DATE_DEBUT_PARAMETER,
            DATE_FIN_PARAMETER,
        ],
        responses={
            200: TradeHistoryResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request, pair):
        """Récupère l'historique des trades pour une paire."""
        try:
            period = request.query_params.get('periode', '24h')
            start_date = request.query_params.get('date_debut')
            end_date = request.query_params.get('date_fin')
            
            if start_date:
                start_date = parse_datetime(start_date)
            if end_date:
                end_date = parse_datetime(end_date)
            
            data = timescale_client.get_trade_history(
                pair,
                period=period if not start_date else None,
                start_date=start_date,
                end_date=end_date
            )
            
            serializer = TradeDataSerializer(data, many=True)
            
            return Response({
                'pair': pair.upper(),
                'count': len(data),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des trades: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArticleHistoryView(APIView):
    """
    API pour récupérer l'historique des articles crypto.
    Endpoint: /api/v1/article/historique
    """
    
    @extend_schema(
        tags=['Articles'],
        operation_id='getArticleHistory',
        summary='Récupérer l\'historique des articles crypto',
        description='''
Retourne l'historique des articles de presse crypto avec leur analyse de sentiment.

## Description

Les articles sont collectés automatiquement depuis des sites spécialisés
(CoinTelegraph, CoinDesk, etc.) et analysés par NLP pour extraire :
- Les crypto-monnaies mentionnées
- Le score et label de sentiment
- Un résumé du contenu

## Sources d'articles

| Source | Type | Fréquence |
|--------|------|-----------|
| CoinTelegraph | News | Temps réel |
| CoinDesk | News | Temps réel |
| Bitcoin Magazine | Analysis | Quotidien |

## Utilisation Frontend

```javascript
// Récupérer les articles sur Bitcoin
const response = await fetch('/api/v1/article/historique/?crypto_symbol=BTC&periode=24h');
const data = await response.json();

// Afficher dans une liste
data.data.forEach(article => {
    const sentimentClass = article.sentiment_label === 'positive' ? 'green' : 
                          article.sentiment_label === 'negative' ? 'red' : 'gray';
    
    articleList.append(`
        <div class="article ${sentimentClass}">
            <h3>${article.title}</h3>
            <p>${article.summary}</p>
            <span>Source: ${article.website}</span>
            <span>Sentiment: ${article.sentiment_score.toFixed(2)}</span>
        </div>
    `);
});
```

## Filtrage par crypto

Utilisez `crypto_symbol` pour filtrer les articles mentionnant une crypto spécifique.
Si non fourni, retourne tous les articles.

## Limites

- Maximum 100 résultats par requête
- Données sur 90 jours glissants
        ''',
        parameters=[
            OpenApiParameter(
                name='crypto_symbol',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filtrer par crypto-monnaie mentionnée (optionnel)',
                examples=[
                    OpenApiExample('Bitcoin', value='BTC'),
                    OpenApiExample('Ethereum', value='ETH'),
                    OpenApiExample('Tous', value=None),
                ]
            ),
            PERIOD_PARAMETER,
            DATE_DEBUT_PARAMETER,
            DATE_FIN_PARAMETER,
        ],
        responses={
            200: ArticleHistoryResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """Récupère l'historique des articles."""
        try:
            crypto_symbol = request.query_params.get('crypto_symbol')
            period = request.query_params.get('periode', '24h')
            start_date = request.query_params.get('date_debut')
            end_date = request.query_params.get('date_fin')
            
            if start_date:
                start_date = parse_datetime(start_date)
            if end_date:
                end_date = parse_datetime(end_date)
            
            data = timescale_client.get_article_history(
                crypto_symbol=crypto_symbol if crypto_symbol else None,
                period=period if not start_date else None,
                start_date=start_date,
                end_date=end_date
            )
            
            serializer = ArticleDataSerializer(data, many=True)
            
            return Response({
                'crypto_symbol': crypto_symbol.upper() if crypto_symbol else 'ALL',
                'count': len(data),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des articles: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AlertHistoryView(APIView):
    """
    API pour récupérer l'historique des alertes de prix.
    Endpoint: /api/v1/alert/historique
    """
    
    @extend_schema(
        tags=['Alerts'],
        operation_id='getAlertHistory',
        summary='Récupérer l\'historique des alertes de prix',
        description='''
Retourne l'historique des alertes générées lors de variations de prix significatives.

## Description

Les alertes sont générées automatiquement lorsque le prix d'une crypto
varie de plus d'un certain pourcentage (seuil par défaut: 1%).

## Types d'alertes

| Type | Description | Couleur suggérée |
|------|-------------|------------------|
| `PRICE_UP` | Hausse significative | 🟢 Vert |
| `PRICE_DOWN` | Baisse significative | 🔴 Rouge |

## Utilisation Frontend

```javascript
// Récupérer les alertes
const response = await fetch('/api/v1/alert/historique/?periode=24h');
const data = await response.json();

// Afficher les notifications
data.data.forEach(alert => {
    const icon = alert.alert_type === 'PRICE_UP' ? '📈' : '📉';
    const color = alert.alert_type === 'PRICE_UP' ? 'green' : 'red';
    
    showNotification({
        title: `${icon} ${alert.pair}`,
        message: `Variation de ${alert.change_percent.toFixed(2)}%`,
        color: color,
        price: alert.last_price
    });
});

// Filtrer par sévérité
const majorAlerts = data.data.filter(a => Math.abs(a.change_percent) > 5);
```

## Seuils de déclenchement

| Seuil | Signification |
|-------|---------------|
| 1% | Variation normale (défaut) |
| 3% | Variation notable |
| 5% | Variation importante |
| 10%+ | Mouvement majeur |

## Limites

- Maximum 500 résultats par requête
- Données sur 90 jours glissants
        ''',
        parameters=[
            OpenApiParameter(
                name='pair',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filtrer par paire de trading (optionnel)',
                examples=[
                    OpenApiExample('Bitcoin', value='XBT/USD'),
                    OpenApiExample('Ethereum', value='ETH/USD'),
                    OpenApiExample('Toutes', value=None),
                ]
            ),
            PERIOD_PARAMETER,
            DATE_DEBUT_PARAMETER,
            DATE_FIN_PARAMETER,
        ],
        responses={
            200: AlertHistoryResponseSerializer,
            500: ErrorResponseSerializer,
        },
    )
    def get(self, request):
        """Récupère l'historique des alertes."""
        try:
            pair = request.query_params.get('pair')
            period = request.query_params.get('periode', '24h')
            start_date = request.query_params.get('date_debut')
            end_date = request.query_params.get('date_fin')
            
            if start_date:
                start_date = parse_datetime(start_date)
            if end_date:
                end_date = parse_datetime(end_date)
            
            data = timescale_client.get_alert_history(
                pair=pair if pair else None,
                period=period if not start_date else None,
                start_date=start_date,
                end_date=end_date
            )
            
            serializer = AlertDataSerializer(data, many=True)
            
            return Response({
                'pair': pair.upper() if pair else 'ALL',
                'count': len(data),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des alertes: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Health'],
    operation_id='healthCheck',
    summary='Vérifier l\'état de santé de l\'API',
    description='''
Endpoint de vérification de santé (health check) du service.

## Description

Retourne l'état actuel du service API. Utilisé pour :
- Monitoring (Prometheus, Grafana)
- Load balancers (healthcheck)
- Déploiement (readiness probe)

## Utilisation

```javascript
// Vérifier si l'API est disponible
async function checkApiHealth() {
    try {
        const response = await fetch('/api/v1/health/');
        const data = await response.json();
        return data.status === 'healthy';
    } catch (error) {
        return false;
    }
}
```

## Réponse

| Champ | Description |
|-------|-------------|
| `status` | État du service (`healthy` ou `unhealthy`) |
| `service` | Nom du service |
| `version` | Version de l'API |
    ''',
    responses={
        200: HealthCheckResponseSerializer,
    },
)
@api_view(['GET'])
def health_check(request):
    """Endpoint de vérification de santé du service."""
    return Response({
        'status': 'healthy',
        'service': 'CRYPTO VIZ API',
        'version': '1.0.0'
    })
