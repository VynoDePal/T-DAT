#!/usr/bin/env python3
"""
Script de health check pour les producteurs de données et services Kafka.
Envoie des métriques à Prometheus et peut déclencher des alertes.
"""
import os
import sys
import time
import psutil
import requests
from datetime import datetime
from confluent_kafka.admin import AdminClient
from prometheus_client import start_http_server, Gauge, Counter, Info

# Métriques Prometheus
producer_up = Gauge('crypto_viz_producer_up', 'Producer health status (1=up, 0=down)', ['producer'])
producer_cpu = Gauge('crypto_viz_producer_cpu_percent', 'Producer CPU usage', ['producer'])
producer_memory = Gauge('crypto_viz_producer_memory_mb', 'Producer memory usage in MB', ['producer'])
kafka_topic_lag = Gauge('crypto_viz_kafka_topic_lag', 'Time since last message in topic', ['topic'])
health_checks_total = Counter('crypto_viz_health_checks_total', 'Total health checks performed')
health_check_failures = Counter('crypto_viz_health_check_failures_total', 'Total health check failures', ['service'])

# Info sur le système
system_info = Info('crypto_viz_system', 'System information')

KAFKA_BOOTSTRAP = os.environ.get('KAFKA_SERVERS', 'localhost:9092')
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '30'))  # secondes
METRICS_PORT = int(os.environ.get('METRICS_PORT', '9999'))

def find_process_by_name(name):
    """Trouve un processus par son nom."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if name in cmdline:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def check_producer_health(producer_name, process_pattern):
    """Vérifie la santé d'un producteur."""
    proc = find_process_by_name(process_pattern)
    
    if proc:
        try:
            cpu_percent = proc.cpu_percent(interval=1)
            memory_mb = proc.memory_info().rss / 1024 / 1024
            
            producer_up.labels(producer=producer_name).set(1)
            producer_cpu.labels(producer=producer_name).set(cpu_percent)
            producer_memory.labels(producer=producer_name).set(memory_mb)
            
            print(f"✅ {producer_name}: UP - CPU: {cpu_percent:.1f}%, MEM: {memory_mb:.1f}MB")
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    producer_up.labels(producer=producer_name).set(0)
    producer_cpu.labels(producer=producer_name).set(0)
    producer_memory.labels(producer=producer_name).set(0)
    health_check_failures.labels(service=producer_name).inc()
    
    print(f"❌ {producer_name}: DOWN")
    return False

def check_kafka_health():
    """Vérifie la santé de Kafka et les topics."""
    try:
        admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP})
        
        # Liste des topics
        topics = admin_client.list_topics(timeout=5)
        
        if topics:
            print(f"✅ Kafka: UP - {len(topics.topics)} topics")
            return True
        else:
            print("⚠️  Kafka: UP but no topics found")
            return True
            
    except Exception as e:
        print(f"❌ Kafka: DOWN - {e}")
        health_check_failures.labels(service='kafka').inc()
        return False

def check_service_endpoint(name, url):
    """Vérifie un endpoint HTTP."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name}: UP")
            return True
    except Exception as e:
        print(f"❌ {name}: DOWN - {e}")
        health_check_failures.labels(service=name).inc()
    return False

def send_alert(service, message):
    """Envoie une alerte (peut être étendu pour intégration avec Alertmanager)."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alert_msg = f"[{timestamp}] ALERT - {service}: {message}"
    print(f"🚨 {alert_msg}")
    
    # Écrire dans un fichier de log d'alertes
    with open('/home/kevyn-odjo/Documents/T-DAT/logs/alerts.log', 'a') as f:
        f.write(alert_msg + '\n')

def main():
    """Boucle principale de health check."""
    print("=" * 80)
    print("🏥 Crypto Viz Health Check Monitor")
    print("=" * 80)
    print(f"📊 Métriques Prometheus: http://localhost:{METRICS_PORT}/metrics")
    print(f"⏱️  Intervalle de vérification: {CHECK_INTERVAL}s")
    print(f"📡 Kafka: {KAFKA_BOOTSTRAP}")
    print("=" * 80)
    
    # Démarrer le serveur de métriques Prometheus
    start_http_server(METRICS_PORT)
    
    # Collecter les infos système
    system_info.info({
        'hostname': os.uname().nodename,
        'os': f"{os.uname().sysname} {os.uname().release}",
        'python_version': sys.version.split()[0]
    })
    
    consecutive_failures = {
        'kraken_producer': 0,
        'article_scraper': 0,
        'kafka': 0
    }
    
    ALERT_THRESHOLD = 3  # Nombre d'échecs consécutifs avant alerte
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 Running health checks...")
            health_checks_total.inc()
            
            # Vérifier les producteurs
            kraken_ok = check_producer_health('kraken_producer', 'kraken_producer.py')
            article_ok = check_producer_health('article_scraper', 'article_scraper.py')
            
            # Vérifier Kafka
            kafka_ok = check_kafka_health()
            
            # Vérifier les services HTTP
            check_service_endpoint('Prometheus', 'http://localhost:9090/-/healthy')
            check_service_endpoint('Grafana', 'http://localhost:3000/api/health')
            check_service_endpoint('Django API', 'http://localhost:8000/api/v1/health/')
            
            # Gérer les alertes pour échecs consécutifs
            services = {
                'kraken_producer': kraken_ok,
                'article_scraper': article_ok,
                'kafka': kafka_ok
            }
            
            for service, is_ok in services.items():
                if not is_ok:
                    consecutive_failures[service] += 1
                    if consecutive_failures[service] == ALERT_THRESHOLD:
                        send_alert(service, f"Service down for {ALERT_THRESHOLD} consecutive checks")
                else:
                    consecutive_failures[service] = 0
            
            print(f"\n✓ Health check completed")
            
        except Exception as e:
            print(f"❌ Error during health check: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Health check monitor stopped")
        sys.exit(0)
