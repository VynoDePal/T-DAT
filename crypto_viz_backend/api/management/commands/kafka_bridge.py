"""
Management command : pont Kafka → Django Channels.
Consomme les topics Kafka et diffuse les messages
vers les groups WebSocket via Redis channel layer.
"""
import json
import logging
import time

from django.core.management.base import BaseCommand
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

SYMBOL_FROM_KRAKEN = {'XBT': 'BTC'}


def _from_kraken(value):
	"""Convertit un symbole Kraken vers le format standard. Ex: XBT/USD → BTC/USD."""
	if value is None:
		return value
	for kraken, std in SYMBOL_FROM_KRAKEN.items():
		value = value.replace(kraken, std)
	return value


TOPIC_CONFIG = {
	'rawticker': {
		'group_prefix': 'ticker',
		'key_field': 'pair',
	},
	'rawtrade': {
		'group_prefix': 'trade',
		'key_field': 'pair',
	},
	'rawarticle': {
		'group_prefix': 'sentiment',
		'key_field': None,
	},
	'rawalert': {
		'group_prefix': 'alert',
		'key_field': None,
	},
}


class Command(BaseCommand):
	help = 'Pont Kafka → Django Channels : diffuse les messages en temps réel'

	def handle(self, *args, **options):
		from kafka import KafkaConsumer

		channel_layer = get_channel_layer()
		group_send = async_to_sync(channel_layer.group_send)

		bootstrap = getattr(
			settings,
			'KAFKA_BOOTSTRAP_SERVERS',
			'kafka:29092',
		)
		topics = list(TOPIC_CONFIG.keys())

		self.stdout.write(self.style.SUCCESS(
			f'Kafka bridge démarré — {bootstrap} — topics: {topics}'
		))

		while True:
			try:
				consumer = KafkaConsumer(
					*topics,
					bootstrap_servers=bootstrap,
					value_deserializer=lambda m: json.loads(m.decode('utf-8')),
					auto_offset_reset='latest',
					enable_auto_commit=True,
					group_id='django_channels_bridge',
					consumer_timeout_ms=1000,
				)
				self.stdout.write(self.style.SUCCESS(
					'Connecté à Kafka, en écoute…'
				))

				for message in consumer:
					try:
						self._dispatch(
							message.topic,
							message.value,
							group_send,
						)
					except Exception as exc:
						logger.error(
							'Erreur dispatch %s: %s',
							message.topic,
							exc,
						)

			except Exception as exc:
				logger.error('Connexion Kafka perdue: %s — retry 5s', exc)
				time.sleep(5)

	def _dispatch(self, topic, data, group_send):
		"""Route un message Kafka vers le bon group Channels."""
		cfg = TOPIC_CONFIG.get(topic)
		if cfg is None:
			return

		prefix = cfg['group_prefix']
		key_field = cfg['key_field']

		if topic == 'rawalert':
			group_send('alert_all', {
				'type': 'send_data',
				'data': data,
			})
			return

		if topic == 'rawarticle':
			cryptos = data.get('cryptocurrencies_mentioned', [])
			sentiment = data.get('sentiment', {})
			for symbol in cryptos:
				group_send(f'sentiment_{symbol}', {
					'type': 'send_data',
					'data': {
						'crypto_symbol': symbol,
						'sentiment_score': sentiment.get('score'),
						'sentiment_label': sentiment.get('label'),
						'title': data.get('title'),
						'website': data.get('website'),
					},
				})
			return

		if key_field and key_field in data:
			pair = data[key_field]
			safe_pair = pair.replace('/', '_')
			group_name = f'{prefix}_{safe_pair}'
			converted_data = dict(data)
			if 'pair' in converted_data:
				converted_data['pair'] = _from_kraken(
					converted_data['pair'],
				)
			group_send(group_name, {
				'type': 'send_data',
				'data': converted_data,
			})
