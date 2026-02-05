"""
Producteur Kafka pour les données de prix et trades depuis Kraken WebSocket.
Récupère dynamiquement la liste des cryptos depuis l'API Django.
"""

import json
import os
import time
import threading
import urllib.request
import websocket
from confluent_kafka import Producer

KAFKA_SERVERS = os.environ.get('KAFKA_SERVERS', 'localhost:9092')
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')

producer_config = {
    'bootstrap.servers': KAFKA_SERVERS,
    'acks': 1,
    'retries': 3,
    'max.in.flight.requests.per.connection': 5,
    'linger.ms': 10,
    'compression.type': 'lz4',
    'batch.size': 32768,
    'socket.keepalive.enable': True,
    'queue.buffering.max.messages': 100000,
    'queue.buffering.max.kbytes': 65536,
}

producer = Producer(producer_config)

WS_URL = "wss://ws.kraken.com"

# Liste par défaut en cas d'indisponibilité de l'API
DEFAULT_PAIRS = [
    "BTC/USD",   # Bitcoin
    "ETH/USD",
    "USDT/USD",
    "SOL/USD",
    "ADA/USD",
    "DOT/USD",
    "LINK/USD"
]

# Variable globale pour stocker les paires actives
kraken_pairs = []

last_prices = {}
PRICE_CHANGE_THRESHOLD = 0.5

def get_active_cryptos_from_api():
    """
    Récupère la liste des cryptos actives depuis l'API Django.
    Retourne une liste de paires au format Kraken (ex: XBT/USD).
    """
    try:
        url = f"{API_BASE_URL}/api/v1/config/crypto/"
        req = urllib.request.Request(url, method='GET')
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extraire les paires de trading actives
            pairs = []
            for crypto in data.get('results', []):
                if crypto.get('is_active', False):
                    symbol = crypto.get('symbol', '')
                    # Kraken utilise XBT au lieu de BTC pour Bitcoin
                    if symbol == 'BTC/USD':
                        symbol = 'XBT/USD'
                    pairs.append(symbol)
            
            if pairs:
                print(f"✓ {len(pairs)} paires récupérées depuis l'API")
                return pairs
            else:
                print("⚠ Aucune crypto active trouvée dans l'API")
                return DEFAULT_PAIRS
                
    except Exception as e:
        print(f"⚠ Erreur API ({e}), utilisation des paires par défaut")
        return DEFAULT_PAIRS

def delivery_report(err, msg):
    """Callback pour les confirmations de livraison."""
    if err is not None:
        print(f'Message delivery failed: {err}')

def send_alert(pair, alert_type, value):
    """Envoie une alerte vers le topic rawalert."""
    payload = {
        "pair": pair,
        "type": alert_type,
        "value": value,
        "timestamp": time.time()
    }
    try:
        producer.produce(
            'rawalert',
            key=pair.encode('utf-8'),
            value=json.dumps(payload).encode('utf-8'),
            callback=delivery_report
        )
        producer.poll(0)
        print(f"ALERT: {pair} - {alert_type} - {value:.2f}%")
    except Exception as e:
        print(f"Kafka alert error: {e}")

def on_error(ws, error):
    """Gestion des erreurs WebSocket."""
    print(f"WebSocket Error: {error}")
    if isinstance(error, Exception):
        print(f"Error type: {type(error).__name__}: {error}")

def on_close(ws, close_status_code, close_msg):
    """Gestion de la fermeture WebSocket."""
    print(f"WebSocket closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Souscription aux canaux Kraken au démarrage."""
    print("WebSocket Kraken connecté")
    
    # Récupérer dynamiquement les paires depuis l'API
    pairs = get_active_cryptos_from_api()
    global kraken_pairs
    kraken_pairs = pairs
    
    # Abonnement ticker
    ws.send(json.dumps({
        "event": "subscribe",
        "pair": pairs,
        "subscription": {"name": "ticker"}
    }))
    print(f"📊 Souscription aux tickers pour {len(pairs)} paires: {', '.join(pairs)}")
    
    # Abonnement trades
    ws.send(json.dumps({
        "event": "subscribe",
        "pair": pairs,
        "subscription": {"name": "trade"}
    }))
    print(f"💱 Souscription aux trades pour {len(pairs)} paires")

def on_message(ws, message):
    """Traitement des messages Kraken."""
    data = json.loads(message)
    
    # Ignorer les heartbeats
    if isinstance(data, dict) and data.get("event") == "heartbeat":
        return
    
    # Ignorer les messages de statut
    if isinstance(data, dict):
        if data.get("event") in ["systemStatus", "subscriptionStatus"]:
            return
    
    # TICKER DATA
    if isinstance(data, list) and len(data) >= 4 and data[-2] == "ticker":
        ticker = data[1]
        pair = data[-1]
        
        last_price = float(ticker["c"][0])
        bid_price = float(ticker["b"][0])
        ask_price = float(ticker["a"][0])
        volume_24h = float(ticker["v"][1])
        timestamp = time.time()
        
        # Calcul du changement de prix
        pct_change = None
        if pair in last_prices:
            previous_price = last_prices[pair]
            pct_change = ((last_price - previous_price) / previous_price) * 100
            
            # Envoyer une alerte si changement significatif
            if abs(pct_change) >= PRICE_CHANGE_THRESHOLD:
                alert_type = "price_spike" if pct_change > 0 else "price_drop"
                send_alert(pair, alert_type, pct_change)
        
        last_prices[pair] = last_price
        
        # Payload pour Kafka
        payload = {
            "pair": pair,
            "last": last_price,
            "bid": bid_price,
            "ask": ask_price,
            "volume_24h": volume_24h,
            "timestamp": timestamp,
            "pct_change": round(pct_change, 2) if pct_change is not None else None
        }
        
        # Envoyer vers Kafka rawticker
        try:
            producer.produce(
                'rawticker',
                key=pair.encode('utf-8'),
                value=json.dumps(payload).encode('utf-8'),
                callback=delivery_report
            )
            producer.poll(0)
            print(f"{pair:12} | Last: ${last_price:>10,.2f} | Change: {payload['pct_change']:>6}% | Vol: {volume_24h:>10,.2f}")
        except Exception as e:
            print(f"Kafka ticker error: {e}")
    
    # TRADE DATA
    if isinstance(data, list) and len(data) >= 4 and data[-2] == "trade":
        pair = data[-1]
        trades = data[1]
        
        for trade in trades:
            payload = {
                "pair": pair,
                "price": float(trade[0]),
                "volume": float(trade[1]),
                "timestamp": float(trade[2]),
                "side": trade[3]  # "b" = buy, "s" = sell
            }
            
            try:
                producer.produce(
                    'rawtrade',
                    key=pair.encode('utf-8'),
                    value=json.dumps(payload).encode('utf-8'),
                    callback=delivery_report
                )
                producer.poll(0)
                side_emoji = "🟢" if payload['side'] == 'b' else "🔴"
                print(f"{side_emoji} {pair:12} | ${payload['price']:>10,.2f} | Vol: {payload['volume']:>8,.4f}")
            except Exception as e:
                print(f"Kafka trade error: {e}")

def periodic_flush():
    """Flush périodique du producteur Kafka."""
    while True:
        time.sleep(2)
        try:
            producer.flush()
        except Exception as e:
            print(f" Flush error: {e}")

if __name__ == "__main__":
    print("=" * 80)
    print("Kraken WebSocket → Kafka Producer")
    print("=" * 80)
    print(f"Kafka: {KAFKA_SERVERS}")
    print(f"Topics: rawticker, rawtrade, rawalert")
    print(f"WebSocket: {WS_URL}")
    print(f"Pairs: {', '.join(get_active_cryptos_from_api())}")
    print("=" * 80)
    print()
    
    # Thread de flush périodique
    threading.Thread(target=periodic_flush, daemon=True).start()
    
    # Connexion WebSocket
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    print("Connexion au WebSocket Kraken...")
    ws.run_forever()
