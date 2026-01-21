"""
Admin configuration pour les métadonnées.
"""
from django.contrib import admin
from .models import CryptoConfiguration, VisualizationParameter, DataCache


@admin.register(CryptoConfiguration)
class CryptoConfigurationAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['symbol', 'name']


@admin.register(VisualizationParameter)
class VisualizationParameterAdmin(admin.ModelAdmin):
    list_display = ['name', 'crypto_symbol', 'time_range', 'user', 'created_at']
    list_filter = ['crypto_symbol', 'time_range']
    search_fields = ['name', 'crypto_symbol']


@admin.register(DataCache)
class DataCacheAdmin(admin.ModelAdmin):
    list_display = ['cache_key', 'expires_at', 'created_at']
    list_filter = ['expires_at']
    search_fields = ['cache_key']
