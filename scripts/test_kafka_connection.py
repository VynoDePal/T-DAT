#!/usr/bin/env python3
"""
Script pour tester la connexion aux topics Kafka.
"""
import sys
from kafka import KafkaConsumer
import json

KAFKA_SERVERS = '20.199.136.163:9092'
TOPICS = ['rawticker', 'rawtrade', 'rawarticle', 'rawalert']

def test_topic(topic_name):
    """Teste la connexion à un topic Kafka."""
    print(f"\n{'='*60}")
    print(f"Test du topic: {topic_name}")
    print('='*60)
    
    try:
        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=KAFKA_SERVERS,
            auto_offset_reset='latest',
            group_id='test-connection-group',
            consumer_timeout_ms=10000,  # 10 secondes de timeout
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        print(f"✓ Connexion établie au topic '{topic_name}'")
        print("Écoute des messages pendant 10 secondes...")
        
        message_count = 0
        for message in consumer:
            message_count += 1
            print(f"\nMessage #{message_count}:")
            print(json.dumps(message.value, indent=2))
            
            if message_count >= 3:  # Limiter à 3 messages
                break
        
        if message_count == 0:
            print("⚠ Aucun message reçu (le topic est peut-être vide)")
        else:
            print(f"\n✓ {message_count} message(s) reçu(s)")
        
        consumer.close()
        return True
        
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False


def main():
    """Teste tous les topics Kafka."""
    print("\n" + "="*60)
    print("CRYPTO VIZ - Test de Connexion Kafka")
    print(f"Serveur: {KAFKA_SERVERS}")
    print("="*60)
    
    results = {}
    for topic in TOPICS:
        results[topic] = test_topic(topic)
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    for topic, success in results.items():
        status = "✓ OK" if success else "✗ ÉCHEC"
        print(f"  {topic:15} : {status}")
    
    print("\n")
    
    # Code de sortie
    if all(results.values()):
        print("✓ Tous les topics sont accessibles!")
        sys.exit(0)
    else:
        print("✗ Certains topics ne sont pas accessibles")
        sys.exit(1)


if __name__ == "__main__":
    main()
