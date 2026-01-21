"""
Modèles Django pour les métadonnées uniquement (stockage SQLite).
Les données de séries temporelles sont stockées dans TimescaleDB et 
ne sont pas gérées par l'ORM Django.
"""
from django.db import models
from django.contrib.auth.models import User


class CryptoConfiguration(models.Model):
    """Configuration des crypto-monnaies suivies."""
    symbol = models.CharField(max_length=10, unique=True, help_text="Ex: BTC, ETH")
    name = models.CharField(max_length=100, help_text="Ex: Bitcoin, Ethereum")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crypto_configuration'
        ordering = ['symbol']
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"


class VisualizationParameter(models.Model):
    """Paramètres de visualisation sauvegardés par utilisateur."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    crypto_symbol = models.CharField(max_length=10)
    time_range = models.CharField(max_length=20, help_text="Ex: 24h, 7d, 30d")
    chart_type = models.CharField(max_length=50, help_text="Ex: candlestick, line")
    indicators = models.JSONField(default=list, help_text="Liste des indicateurs actifs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'visualization_parameters'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.crypto_symbol}"


class DataCache(models.Model):
    """Cache temporaire pour résultats agrégés fréquents."""
    cache_key = models.CharField(max_length=255, unique=True)
    cache_value = models.JSONField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'data_cache'
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return self.cache_key
