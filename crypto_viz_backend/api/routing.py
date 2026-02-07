"""
Routes WebSocket pour le streaming temps réel.
"""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
	re_path(
		r'ws/ticker/(?P<base>\w+)/(?P<quote>\w+)/$',
		consumers.TickerConsumer.as_asgi(),
	),
	re_path(
		r'ws/trade/(?P<base>\w+)/(?P<quote>\w+)/$',
		consumers.TradeConsumer.as_asgi(),
	),
	re_path(
		r'ws/sentiment/(?P<symbol>\w+)/$',
		consumers.SentimentConsumer.as_asgi(),
	),
	re_path(
		r'ws/prediction/(?P<symbol>\w+)/$',
		consumers.PredictionConsumer.as_asgi(),
	),
	re_path(r'ws/alert/$', consumers.AlertConsumer.as_asgi()),
]
