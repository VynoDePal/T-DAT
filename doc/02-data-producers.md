# Data Producers - Guide Technique

## Vue d'ensemble

Les **Data Producers** sont la couche d'ingestion initiale du pipeline CRYPTO VIZ. Ils collectent les données brutes depuis des sources externes et les publient vers Apache Kafka.

| Producer | Source | Type | Fréquence | Topic Kafka |
|----------|--------|------|-----------|-------------|
| `article_scraper.py` | RSS Feeds (5 sources) | Pull | 5 minutes | `rawarticle` |
| `kraken_producer.py` | WebSocket Kraken | Push | Temps réel | `rawticker`, `rawtrade`, `rawalert` |

---

## 1. Article Scraper (`data_producers/article_scraper.py`)

### 1.1 Architecture du composant

```
┌─────────────────────────────────────────────────────────────────┐
│                     ARTICLE SCRAPER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ RSS Sources  │  │   Parsing    │  │  Enrichment  │          │
│  │              │  │              │  │              │          │
│  │ • CoinDesk   │  │ feedparser   │  │ • Content    │          │
│  │ • Cointele   │  │              │  │   extract    │          │
│  │ • Decrypt    │──┼──────────────┼──▶│ • Sentiment  │          │
│  │ • CryptoSlate│  │ BeautifulSoup│  │   analysis   │          │
│  │ • BitcoinMag │  │              │  │ • Crypto tags│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│          │                                    │                 │
│          │    ┌───────────────────────────────┘                 │
│          │    │                                                 │
│          ▼    ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Kafka Producer                            ││
│  │  • Topic: rawarticle                                         ││
│  │  • Key: source_name (ex: "CoinDesk")                         ││
│  │  • Value: JSON payload                                       ││
│  │  • Compression: LZ4                                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Flux d'exécution détaillé

```python
# ÉTAPE 1: Configuration Kafka
producer_config = {
    'bootstrap.servers': 'localhost:9092',
    'acks': 1,                          # Attendre confirmation leader
    'retries': 3,                       # 3 tentatives en cas d'échec
    'linger.ms': 100,                   # Buffer 100ms pour batching
    'compression.type': 'lz4',            # Compression rapide
    'batch.size': 65536,                # 64KB batches
}

# ÉTAPE 2: Boucle principale (cycle 5 minutes)
while True:
    for source_name, feed_url in RSS_FEEDS.items():
        
        # 2a. Parse RSS feed
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries[:10]:  # Limite 10 articles/source
            
            # 2b. Extraction données de base
            article_url = entry.get('link')
            title = entry.get('title')
            summary = entry.get('summary')
            published = entry.get('published')
            
            # 2c. Nettoyage HTML
            summary_soup = BeautifulSoup(summary, 'html.parser')
            clean_summary = summary_soup.get_text().strip()[:500]
            
            # 2d. Extraction contenu complet (optionnel)
            content = extract_article_content(article_url)
            
            # 2e. Analyse sentiment
            sentiment_text = f"{title} {clean_summary}"
            sentiment = analyze_sentiment(sentiment_text)
            # → {'score': 0.75, 'label': 'positive'}
            
            # 2f. Extraction cryptos mentionnées
            crypto_symbols = extract_crypto_tags(sentiment_text)
            # → ['bitcoin', 'btc', 'crypto']
            
            # 2g. Construction payload
            payload = {
                'id': article_url,
                'title': title,
                'url': article_url,
                'website': source_name,
                'summary': clean_summary,
                'content': {'text': content} if content else {},
                'published_at': timestamp_unix,
                'scraped_at': time.time(),
                'tags': crypto_symbols,
                'sentiment': sentiment,
                'cryptocurrencies_mentioned': crypto_symbols
            }
            
            # 2h. Envoi Kafka
            producer.produce(
                topic='rawarticle',
                key=source_name.encode('utf-8'),
                value=json.dumps(payload).encode('utf-8'),
                callback=delivery_report
            )
    
    # 2i. Attente prochain cycle
    time.sleep(300)  # 5 minutes
```

### 1.3 Analyse de sentiment (TextBlob)

```python
def analyze_sentiment(text):
    """
    Convertit la polarity TextBlob [-1, 1] en score [0, 1]
    pour compatibilité avec le schéma Spark.
    
    TextBlob Sentiment:
    - polarity: -1.0 (négatif) à +1.0 (positif)
    - subjectivity: 0.0 (objectif) à 1.0 (subjectif)
    
    Conversion projet:
    - score = (polarity + 1) / 2  # Mapping [-1,1] → [0,1]
    
    Classification:
    - score > 0.6 → 'positive'
    - score < 0.4 → 'negative'
    - else → 'neutral'
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity      # Ex: +0.5
    
    score = (polarity + 1) / 2               # Ex: (0.5 + 1) / 2 = 0.75
    
    if score > 0.6:
        label = 'positive'
    elif score < 0.4:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {'score': round(score, 4), 'label': label}
    # Ex: {'score': 0.75, 'label': 'positive'}
```

### 1.4 Extraction des cryptos

```python
def extract_crypto_tags(text):
    """
    Extrait les mots-clés crypto du texte.
    Retourne max 10 tags uniques.
    """
    crypto_keywords = {
        'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
        'blockchain', 'defi', 'nft', 'altcoin', 'mining', 'wallet',
        'solana', 'cardano', 'polkadot', 'chainlink', 'polygon', 'matic',
        'binance', 'coinbase', 'kraken', 'exchange', 'trading'
    }
    
    text_lower = text.lower()
    found_tags = []
    
    for keyword in crypto_keywords:
        if keyword in text_lower:
            found_tags.append(keyword)
    
    return list(set(found_tags))[:10]  # Dédoublonnage + limite
```

### 1.5 Extraction de contenu HTML

```python
def extract_article_content(url, timeout=10):
    """
    Extrait le contenu texte principal d'une page article.
    Utilise BeautifulSoup pour parser le HTML.
    """
    # Requête HTTP
    response = requests.get(url, timeout=timeout, headers={
        'User-Agent': 'Mozilla/5.0 (...)'
    })
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Supprimer éléments non pertinents
    for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        element.decompose()
    
    # Stratégie 1: Chercher <article>
    content = ''
    article = soup.find('article')
    if article:
        paragraphs = article.find_all('p')
        content = ' '.join([p.get_text().strip() 
                          for p in paragraphs 
                          if len(p.get_text().strip()) > 50])
    
    # Stratégie 2: Fallback sur tous les <p>
    if not content:
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text().strip() 
                          for p in paragraphs[:5] 
                          if len(p.get_text().strip()) > 50])
    
    return content[:2000] if content else None  # Limite 2000 caractères
```

### 1.6 Format de sortie (Message Kafka)

```json
{
  "id": "https://www.coindesk.com/bitcoin-hits-100k",
  "title": "Bitcoin Hits $100K Amid Institutional Adoption",
  "url": "https://www.coindesk.com/bitcoin-hits-100k",
  "website": "CoinDesk",
  "summary": "Bitcoin reached a new all-time high today as institutional investors...",
  "content": {
    "text": "Full article content extracted from HTML..."
  },
  "published_at": 1705312800.123,
  "scraped_at": 1705312950.456,
  "tags": ["bitcoin", "btc", "crypto", "institutional"],
  "sentiment": {
    "score": 0.8234,
    "label": "positive"
  },
  "cryptocurrencies_mentioned": ["bitcoin", "btc", "crypto", "institutional"]
}
```

---

## 2. Kraken Producer (`data_producers/kraken_producer.py`)

### 2.1 Architecture du composant

```
┌─────────────────────────────────────────────────────────────────┐
│                     KRAKEN PRODUCER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐│
│  │  WebSocket       │  │  Message Parser  │  │  Alert Detector  ││
│  │  Connection      │  │                  │  │                  ││
│  │                  │  │ • ticker: price  │  │ price_change     ││
│  │ wss://ws.kraken  │──▶│   volume         │──▶│ > threshold?    ││
│  │ .com             │  │ • trade: vol     │  │   (0.5%)        ││
│  │                  │  │   side           │  │                  ││
│  │ Subscriptions:   │  │ • heartbeat      │  │ → rawalert       ││
│  │ • ticker         │  │ • status         │  │                  ││
│  │ • trade          │  │                  │  │                  ││
│  └──────────────────┘  └──────────────────┘  └──────────────────┘│
│           │                     │                     │          │
│           │    ┌────────────────┴─────────────────────┘          │
│           │    │                                               │
│           ▼    ▼                                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Kafka Producer                          ││
│  │                                                             ││
│  │  Topics:                                                    ││
│  │  • rawticker  → Ticker data (prix temps réel)              ││
│  │  • rawtrade   → Trade data (transactions)                  ││
│  │  • rawalert   → Price alerts (changements >0.5%)          ││
│  │                                                             ││
│  │  Keys: pair (XBT/USD)                                       ││
│  │  Compression: LZ4                                           ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Flux d'exécution détaillé

```python
# ÉTAPE 1: Configuration
WS_URL = "wss://ws.kraken.com"
PAIRS = ["XBT/USD", "ETH/USD", "USDT/USD", "SOL/USD", 
         "ADA/USD", "MATIC/USD", "DOT/USD", "LINK/USD"]
PRICE_CHANGE_THRESHOLD = 0.5  # 0.5%

# ÉTAPE 2: Callbacks WebSocket
def on_open(ws):
    """Souscription aux canaux au démarrage."""
    # Souscription ticker
    ws.send(json.dumps({
        "event": "subscribe",
        "pair": PAIRS,
        "subscription": {"name": "ticker"}
    }))
    
    # Souscription trade
    ws.send(json.dumps({
        "event": "subscribe",
        "pair": PAIRS,
        "subscription": {"name": "trade"}
    }))

def on_message(ws, message):
    """Traitement des messages Kraken."""
    data = json.loads(message)
    
    # Ignorer heartbeats et status
    if isinstance(data, dict) and data.get("event") in ["heartbeat", "systemStatus"]:
        return
    
    # === MESSAGE TICKER ===
    if isinstance(data, list) and len(data) >= 4 and data[-2] == "ticker":
        process_ticker_message(data)
    
    # === MESSAGE TRADE ===
    if isinstance(data, list) and len(data) >= 4 and data[-2] == "trade":
        process_trade_message(data)

# ÉTAPE 3: Traitement ticker
def process_ticker_message(data):
    """
    Format message Kraken ticker:
    [channelID, {
        'a': [ask_price, ask_whole_lot_volume, ask_lot_volume],
        'b': [bid_price, ...],
        'c': [last_price, last_lot_volume],
        'v': [volume_today, volume_24h],
        ...
    }, 'ticker', 'XBT/USD']
    """
    ticker_data = data[1]
    pair = data[-1]
    
    # Extraction prix
    last_price = float(ticker_data["c"][0])   # Prix last
    bid_price = float(ticker_data["b"][0])    # Prix bid
    ask_price = float(ticker_data["a"][0])    # Prix ask
    volume_24h = float(ticker_data["v"][1])   # Volume 24h
    
    # Calcul changement prix
    pct_change = None
    if pair in last_prices:
        previous = last_prices[pair]
        pct_change = ((last_price - previous) / previous) * 100
        
        # Détection alerte
        if abs(pct_change) >= PRICE_CHANGE_THRESHOLD:
            send_price_alert(pair, pct_change)
    
    last_prices[pair] = last_price
    
    # Payload ticker
    payload = {
        "pair": pair,
        "last": last_price,
        "bid": bid_price,
        "ask": ask_price,
        "volume_24h": volume_24h,
        "timestamp": time.time(),
        "pct_change": round(pct_change, 2) if pct_change else None
    }
    
    # Envoi Kafka
    producer.produce(
        topic='rawticker',
        key=pair.encode('utf-8'),
        value=json.dumps(payload).encode('utf-8')
    )

# ÉTAPE 4: Traitement trade
def process_trade_message(data):
    """
    Format message Kraken trade:
    [channelID, [
        [price, volume, time, side, orderType, misc],
        ...
    ], 'trade', 'XBT/USD']
    """
    pair = data[-1]
    trades = data[1]  # Liste des trades
    
    for trade in trades:
        payload = {
            "pair": pair,
            "price": float(trade[0]),
            "volume": float(trade[1]),
            "timestamp": float(trade[2]),
            "side": trade[3]  # "b" = buy, "s" = sell
        }
        
        producer.produce(
            topic='rawtrade',
            key=pair.encode('utf-8'),
            value=json.dumps(payload).encode('utf-8')
        )

# ÉTAPE 5: Envoi alerte
def send_price_alert(pair, pct_change):
    """Envoie une alerte si changement significatif."""
    alert_type = "price_spike" if pct_change > 0 else "price_drop"
    
    payload = {
        "pair": pair,
        "type": alert_type,
        "last": last_prices[pair],
        "change": pct_change,
        "threshold": PRICE_CHANGE_THRESHOLD,
        "timestamp": time.time()
    }
    
    producer.produce(
        topic='rawalert',
        key=pair.encode('utf-8'),
        value=json.dumps(payload).encode('utf-8')
    )
```

### 2.3 Formats de messages Kraken

#### Message Ticker (Kraken → Producer)
```json
// Exemple message reçu du WebSocket Kraken
[
  1234,
  {
    "a": ["100000.5", "5", "5.00000000"],
    "b": ["99950.0", "3", "3.00000000"],
    "c": ["99950.5", "0.50000000"],
    "v": ["1500.5", "15000.5"],
    "p": ["98500.0", "99000.5"],
    "t": [500, 5000],
    "l": ["98000.0", "97500.0"],
    "h": ["101000.0", "102000.0"],
    "o": ["98000.0"]
  },
  "ticker",
  "XBT/USD"
]

// Mapping des champs:
// a = ask, b = bid, c = close/last, v = volume
// p = vwap, t = trades count, l = low, h = high, o = open
```

#### Message Trade (Kraken → Producer)
```json
// Exemple message trade
[
  1234,
  [
    ["99950.5", "0.5", "1705312345.678", "b", "l", ""],
    ["99951.0", "0.3", "1705312345.890", "s", "l", ""]
  ],
  "trade",
  "XBT/USD"
]

// Format par trade: [price, volume, time, side, orderType, misc]
// side: "b" = buy, "s" = sell
```

### 2.4 Formats de sortie (Messages Kafka)

#### rawticker
```json
{
  "pair": "XBT/USD",
  "last": 99950.50,
  "bid": 99950.00,
  "ask": 100000.50,
  "volume_24h": 15000.5,
  "timestamp": 1705312345.678,
  "pct_change": 2.51
}
```

#### rawtrade
```json
{
  "pair": "XBT/USD",
  "price": 99950.50,
  "volume": 0.5,
  "timestamp": 1705312345.678,
  "side": "b"
}
```

#### rawalert
```json
{
  "pair": "XBT/USD",
  "type": "price_spike",
  "last": 99950.50,
  "change": 2.51,
  "threshold": 0.5,
  "timestamp": 1705312345.678
}
```

---

## 3. Configuration Kafka commune

### 3.1 Paramètres de production

```python
# Configuration optimisée pour latence vs throughput
producer_config = {
    # Connexion
    'bootstrap.servers': 'localhost:9092',
    
    # Durabilité
    'acks': 1,                    # 1 = leader confirme (équilibre perf/safety)
                                  # 0 = fire-and-forget (max perf)
                                  # all = tous replicas (max safety)
    
    # Retry
    'retries': 3,                 # 3 tentatives
    'retry.backoff.ms': 100,      # Attente 100ms entre retries
    
    # Batching (throughput)
    'batch.size': 65536,          # 64KB batch
    'linger.ms': 100,             # Attendre 100ms pour batch
    
    # Buffering
    'queue.buffering.max.messages': 100000,
    'queue.buffering.max.kbytes': 65536,
    
    # Compression
    'compression.type': 'lz4',    # Rapide et efficace
    
    # Keepalive
    'socket.keepalive.enable': True,
}
```

### 3.2 Callback de livraison

```python
def delivery_report(err, msg):
    """Callback appelé après tentative de livraison."""
    if err is not None:
        print(f'Message delivery failed: {err}')
        # Log l'erreur, possible retry manuel
    else:
        # Message livré avec succès
        pass  # Optionnel: logging debug
```

### 3.3 Gestion des erreurs

```python
# Pattern: Try/Except + Log
try:
    producer.produce(
        topic='rawarticle',
        key=key,
        value=value,
        callback=delivery_report
    )
    producer.poll(0)  # Non-bloquant
except BufferError:
    # Buffer plein, attente et retry
    producer.poll(1)
    producer.produce(topic, key, value)
except Exception as e:
    # Log erreur critique
    print(f"Erreur production: {e}")

# Flush périodique pour garantir livraison
producer.flush()  # Bloquant jusqu'à confirmation
```

---

## 4. Tableaux récapitulatifs

### 4.1 Sources RSS supportées

| Source | URL | Langue | Fréquence moyenne |
|--------|-----|--------|-------------------|
| CoinDesk | coindesk.com/arc/outboundfeeds/rss/ | EN | ~20 articles/jour |
| Cointelegraph | cointelegraph.com/rss | EN | ~30 articles/jour |
| Decrypt | decrypt.co/feed | EN | ~15 articles/jour |
| CryptoSlate | cryptoslate.com/feed/ | EN | ~25 articles/jour |
| Bitcoin Magazine | bitcoinmagazine.com/.rss/full/ | EN | ~10 articles/jour |

### 4.2 Paires Kraken suivies

| Paire | Crypto | Fiat | Type |
|-------|--------|------|------|
| XBT/USD | Bitcoin | USD | Majeur |
| ETH/USD | Ethereum | USD | Majeur |
| USDT/USD | Tether | USD | Stablecoin |
| SOL/USD | Solana | USD | Altcoin |
| ADA/USD | Cardano | USD | Altcoin |
| MATIC/USD | Polygon | USD | Altcoin |
| DOT/USD | Polkadot | USD | Altcoin |
| LINK/USD | Chainlink | USD | Altcoin |

### 4.3 Topics Kafka et schémas

| Topic | Clé | Fréquence | Rétention | Partition |
|-------|-----|-----------|-----------|-----------|
| rawarticle | source | ~50 msg/jour | 7 jours | 1 |
| rawticker | pair | ~10 msg/sec | 7 jours | 1 |
| rawtrade | pair | ~100 msg/sec | 7 jours | 1 |
| rawalert | pair | ~5 msg/heure | 1 jour | 1 |

---

**Suite** : [03-kafka.md](./03-kafka.md) pour la configuration et gestion de Kafka.
