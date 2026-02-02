#!/usr/bin/env python3
"""
Scraper d'articles crypto pour Kafka.
Collecte les articles depuis plusieurs sources RSS et les envoie vers rawarticle.
"""

import json
import os
import time
import feedparser
import requests
from confluent_kafka import Producer
from datetime import datetime
from bs4 import BeautifulSoup
from textblob import TextBlob

KAFKA_SERVERS = os.environ.get('KAFKA_SERVERS', 'localhost:9092')

producer_config = {
    'bootstrap.servers': KAFKA_SERVERS,
    'acks': 1,
    'retries': 3,
    'linger.ms': 100,
    'compression.type': 'lz4',
    'batch.size': 65536,
    'queue.buffering.max.messages': 100000,
    'queue.buffering.max.kbytes': 65536,
}

producer = Producer(producer_config)

RSS_FEEDS = {
    'CoinDesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    'Cointelegraph': 'https://cointelegraph.com/rss',
    'Decrypt': 'https://decrypt.co/feed',
    'CryptoSlate': 'https://cryptoslate.com/feed/',
    'Bitcoin Magazine': 'https://bitcoinmagazine.com/.rss/full/',
}

seen_articles = set()
SCRAPE_INTERVAL = 300  # 5 minutes

def delivery_report(err, msg):
    """Callback pour les confirmations de livraison."""
    if err is not None:
        print(f'Message delivery failed: {err}')

def extract_article_content(url, timeout=10):
    """Tente d'extraire le contenu principal de l'article."""
    try:
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Supprimer les éléments non pertinents
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Chercher le contenu principal
        content = ''
        article = soup.find('article')
        if article:
            paragraphs = article.find_all('p')
            content = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
        
        # Fallback: tous les paragraphes
        if not content:
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text().strip() for p in paragraphs[:5] if len(p.get_text().strip()) > 50])
        
        return content[:2000] if content else None
    except Exception as e:
        print(f"Erreur extraction contenu de {url}: {e}")
        return None

def scrape_feed(source_name, feed_url):
    """Scrape un flux RSS et envoie les nouveaux articles vers Kafka."""
    print(f"Scraping {source_name}...")
    
    try:
        feed = feedparser.parse(feed_url)
        new_articles_count = 0
        
        for entry in feed.entries[:10]:  # Limiter à 10 articles par source
            article_url = entry.get('link', '')
            
            # Éviter les doublons
            if article_url in seen_articles:
                continue
            
            seen_articles.add(article_url)
            
            # Extraction des données de base
            title = entry.get('title', 'No title')
            published = entry.get('published', '')
            summary = entry.get('summary', '')
            
            # Nettoyer le résumé HTML
            if summary:
                summary_soup = BeautifulSoup(summary, 'html.parser')
                summary = summary_soup.get_text().strip()[:500]
            
            # Timestamp
            try:
                if published:
                    pub_time = time.mktime(time.strptime(published, '%a, %d %b %Y %H:%M:%S %z'))
                else:
                    pub_time = time.time()
            except:
                pub_time = time.time()
            
            # Extraire le contenu complet (optionnel, peut être lent)
            content = extract_article_content(article_url, timeout=5) if article_url else None
            
            # Analyser le sentiment sur titre + résumé
            sentiment_text = f"{title} {summary}"
            sentiment = analyze_sentiment(sentiment_text)
            
            # Extraire les cryptos mentionnées
            crypto_symbols = extract_crypto_tags(title + ' ' + summary)
            
            # Payload pour Kafka (compatible avec schéma Spark)
            payload = {
                'id': article_url or str(time.time()),
                'title': title,
                'url': article_url,
                'website': source_name,
                'summary': summary,
                'content': {'text': content} if content else {},
                'published_at': pub_time,
                'scraped_at': time.time(),
                'tags': crypto_symbols,
                'sentiment': sentiment,
                'cryptocurrencies_mentioned': crypto_symbols
            }
            
            # Envoyer vers Kafka
            try:
                producer.produce(
                    'rawarticle',
                    key=source_name.encode('utf-8'),
                    value=json.dumps(payload).encode('utf-8'),
                    callback=delivery_report
                )
                producer.poll(0)
                new_articles_count += 1
                print(f"[{source_name}] {title[:60]}...")
            except Exception as e:
                print(f"Kafka error: {e}")
        
        producer.flush()
        
        if new_articles_count > 0:
            print(f"{new_articles_count} nouveaux articles de {source_name}")
        else:
            print(f"Aucun nouvel article de {source_name}")
            
    except Exception as e:
        print(f"Erreur scraping {source_name}: {e}")

def extract_crypto_tags(text):
    """Extrait les tags crypto du texte."""
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
    
    return list(set(found_tags))[:10]  # Max 10 tags uniques

def analyze_sentiment(text):
    """
    Analyse le sentiment d'un texte avec TextBlob.
    Convertit la polarity [-1, 1] en score [0, 1] pour compatibilité Spark.
    
    Args:
        text: Texte à analyser
        
    Returns:
        dict: {'score': float (0-1), 'label': str ('positive'|'negative'|'neutral')}
    """
    try:
        if not text or not isinstance(text, str):
            return {'score': 0.5, 'label': 'neutral'}
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1.0 à 1.0
        
        # Convertir en score 0-1
        score = (polarity + 1) / 2
        
        # Déterminer le label selon les seuils Spark
        if score > 0.6:
            label = 'positive'
        elif score < 0.4:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {'score': round(score, 4), 'label': label}
    
    except Exception as e:
        print(f"Erreur analyse sentiment: {e}")
        return {'score': 0.5, 'label': 'neutral'}

def extract_crypto_symbols(text):
    """
    Extrait les symboles de cryptomonnaies mentionnés dans le texte.
    Version renommée pour compatibilité avec le schéma Spark.
    
    Args:
        text: Texte à analyser
        
    Returns:
        list: Liste des symboles crypto (ex: ['BTC', 'ETH', 'SOL'])
    """

def main():
    print("=" * 80)
    print("Crypto Article Scraper → Kafka Producer")
    print("=" * 80)
    print(f"Kafka: {KAFKA_SERVERS}")
    print(f"Topic: rawarticle")
    print(f"Sources RSS: {len(RSS_FEEDS)}")
    for source in RSS_FEEDS.keys():
        print(f"   - {source}")
    print(f"⏱️  Intervalle: {SCRAPE_INTERVAL}s ({SCRAPE_INTERVAL//60} minutes)")
    print("=" * 80)
    print()
    
    iteration = 0
    
    while True:
        iteration += 1
        print(f"\n{'='*80}")
        print(f"🔄 Cycle {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        for source_name, feed_url in RSS_FEEDS.items():
            scrape_feed(source_name, feed_url)
            time.sleep(2)  # Pause entre chaque source
        
        print(f"\nCycle {iteration} terminé. Articles vus: {len(seen_articles)}")
        print(f"Prochain scraping dans {SCRAPE_INTERVAL}s...\n")
        
        time.sleep(SCRAPE_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nArrêt du scraper...")
        producer.close()
        print("Producteur Kafka fermé proprement")
