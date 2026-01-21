"""
URLs pour l'API CRYPTO VIZ.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CryptoConfigurationViewSet,
    VisualizationParameterViewSet,
    SentimentHistoryView,
    PredictionHistoryView,
    TickerHistoryView,
    TradeHistoryView,
    ArticleHistoryView,
    AlertHistoryView,
    health_check,
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'config/crypto', CryptoConfigurationViewSet, basename='crypto-config')
router.register(r'config/visualization', VisualizationParameterViewSet, basename='viz-config')

urlpatterns = [
    # Health check
    path('health/', health_check, name='health-check'),
    
    # APIs pour données historiques depuis TimescaleDB
    path('sentiment/<str:crypto_symbol>/historique/', 
         SentimentHistoryView.as_view(), 
         name='sentiment-history'),
    
    path('prediction/<str:crypto_symbol>/historique/', 
         PredictionHistoryView.as_view(), 
         name='prediction-history'),
    
    path('ticker/<str:pair>/historique/', 
         TickerHistoryView.as_view(), 
         name='ticker-history'),
    
    path('trade/<str:pair>/historique/', 
         TradeHistoryView.as_view(), 
         name='trade-history'),
    
    path('article/historique/', 
         ArticleHistoryView.as_view(), 
         name='article-history'),
    
    path('alert/historique/', 
         AlertHistoryView.as_view(), 
         name='alert-history'),
    
    # Include router URLs
    path('', include(router.urls)),
]
