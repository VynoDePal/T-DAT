"""
WebSocket consumers pour le streaming temps réel.
Chaque consumer rejoint un group Redis et diffuse les données
envoyées par le kafka_bridge.
"""
import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)

SYMBOL_TO_KRAKEN = {'BTC': 'XBT'}


def _kraken_base(base):
	"""Convertit un symbole standard vers Kraken pour le group name."""
	return SYMBOL_TO_KRAKEN.get(base.upper(), base.upper())


class TickerConsumer(AsyncJsonWebsocketConsumer):
	"""Diffuse les tickers en temps réel pour une paire donnée."""

	async def connect(self):
		base = self.scope['url_route']['kwargs']['base']
		quote = self.scope['url_route']['kwargs']['quote']
		self.pair = f'{base}/{quote}'
		kraken_base = _kraken_base(base)
		self.group_name = f'ticker_{kraken_base}_{quote}'

		await self.channel_layer.group_add(
			self.group_name,
			self.channel_name,
		)
		await self.accept()
		logger.info('WS ticker connecté: %s', self.pair)

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(
			self.group_name,
			self.channel_name,
		)

	async def send_data(self, event):
		await self.send_json(event['data'])


class TradeConsumer(AsyncJsonWebsocketConsumer):
	"""Diffuse les trades en temps réel pour une paire donnée."""

	async def connect(self):
		base = self.scope['url_route']['kwargs']['base']
		quote = self.scope['url_route']['kwargs']['quote']
		self.pair = f'{base}/{quote}'
		kraken_base = _kraken_base(base)
		self.group_name = f'trade_{kraken_base}_{quote}'

		await self.channel_layer.group_add(
			self.group_name,
			self.channel_name,
		)
		await self.accept()
		logger.info('WS trade connecté: %s', self.pair)

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(
			self.group_name,
			self.channel_name,
		)

	async def send_data(self, event):
		await self.send_json(event['data'])


class SentimentConsumer(AsyncJsonWebsocketConsumer):
	"""Diffuse le sentiment en temps réel pour un symbole crypto."""

	async def connect(self):
		self.symbol = self.scope['url_route']['kwargs']['symbol']
		self.group_name = f'sentiment_{self.symbol}'

		await self.channel_layer.group_add(
			self.group_name,
			self.channel_name,
		)
		await self.accept()
		logger.info('WS sentiment connecté: %s', self.symbol)

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(
			self.group_name,
			self.channel_name,
		)

	async def send_data(self, event):
		await self.send_json(event['data'])


class PredictionConsumer(AsyncJsonWebsocketConsumer):
	"""Diffuse les prédictions en temps réel pour un symbole crypto."""

	async def connect(self):
		self.symbol = self.scope['url_route']['kwargs']['symbol']
		self.group_name = f'prediction_{self.symbol}'

		await self.channel_layer.group_add(
			self.group_name,
			self.channel_name,
		)
		await self.accept()
		logger.info('WS prediction connecté: %s', self.symbol)

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(
			self.group_name,
			self.channel_name,
		)

	async def send_data(self, event):
		await self.send_json(event['data'])


class AlertConsumer(AsyncJsonWebsocketConsumer):
	"""Diffuse toutes les alertes en temps réel."""

	async def connect(self):
		self.group_name = 'alert_all'

		await self.channel_layer.group_add(
			self.group_name,
			self.channel_name,
		)
		await self.accept()
		logger.info('WS alert connecté')

	async def disconnect(self, close_code):
		await self.channel_layer.group_discard(
			self.group_name,
			self.channel_name,
		)

	async def send_data(self, event):
		await self.send_json(event['data'])
