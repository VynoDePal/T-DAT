# 🚀 Guide de Démarrage Rapide - CRYPTO VIZ

Guide condensé pour démarrer rapidement le projet.

## ⚡ Démarrage en 5 Minutes

### 1. Prérequis
```bash
# Vérifier les installations
python3 --version  # >= 3.11
docker --version
docker compose version
java -version      # >= 11 (pour Spark)
```

### 2. Configuration Initiale
```bash
# Cloner et configurer
cd /home/kevyn-odjo/Documents/T-DAT
cp .env.example .env

# Éditer .env si nécessaire (surtout les mots de passe)
nano .env
```

### 3. Démarrage Automatique
```bash
# Créer le répertoire de logs
mkdir -p logs

# Rendre les scripts exécutables
chmod +x scripts/*.sh

# Démarrer tous les services
./scripts/start_all.sh
```

**C'est tout!** Les services se lancent automatiquement :
- ✅ TimescaleDB (port 15432)
- ✅ Redis (port 6380)
- ✅ Django API (port 8000)
- ✅ Spark Ingestion
- ✅ Spark Analytics

### 4. Vérification

**Tester l'API :**
```bash
curl http://localhost:8000/api/v1/health/
```

**Tester Kafka :**
```bash
python3 scripts/test_kafka_connection.py
```

**Tester TimescaleDB :**
```bash
python3 scripts/test_timescale_connection.py
```

### 5. Arrêt des Services
```bash
./scripts/stop_all.sh
```

## 📊 Premiers Tests API

### Récupérer le sentiment BTC (24h)
```bash
curl "http://localhost:8000/api/v1/sentiment/BTC/historique/?periode=24h"
```

### Récupérer les prix ETH/USD (1h)
```bash
curl "http://localhost:8000/api/v1/ticker/ETH/USD/historique/?periode=1h"
```

### Récupérer les articles récents
```bash
curl "http://localhost:8000/api/v1/article/historique/?crypto_symbol=BTC&periode=24h"
```

## 🔧 Commandes Utiles

### Django
```bash
cd crypto_viz_backend
source venv/bin/activate

# Créer un superuser
python manage.py createsuperuser

# Ouvrir le shell Django
python manage.py shell

# Voir les migrations
python manage.py showmigrations
```

### TimescaleDB
```bash
# Se connecter à la base
docker exec -it crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts

# Voir les tables
\dt

# Voir les hypertables
SELECT * FROM timescaledb_information.hypertables;

# Compter les données
SELECT COUNT(*) FROM ticker_data;
```

### Logs en Temps Réel
```bash
# Django
tail -f logs/django.log

# Spark Ingestion
tail -f logs/spark_ingestion.log

# Spark Analytics
tail -f logs/spark_analytics.log

# TimescaleDB
docker logs -f crypto_viz_timescaledb
```

## 🐛 Résolution de Problèmes

### TimescaleDB ne démarre pas
```bash
# Supprimer et recréer les volumes
docker compose down -v
docker compose up -d timescaledb
```

### Erreur de connexion Kafka
```bash
# Vérifier que le serveur Kafka est accessible
telnet 20.199.136.163 9092

# Tester avec le script
python3 scripts/test_kafka_connection.py
```

### Django ne démarre pas
```bash
cd crypto_viz_backend
source venv/bin/activate

# Réinstaller les dépendances
pip install -r requirements.txt

# Vérifier les migrations
python manage.py migrate

# Démarrer manuellement
python manage.py runserver 0.0.0.0:8000
```

### Spark ne démarre pas
```bash
cd spark_jobs
source venv/bin/activate

# Vérifier les dépendances
pip install -r requirements.txt

# Tester la connexion Kafka
python -c "from kafka import KafkaConsumer; print('OK')"

# Lancer manuellement
python kafka_to_timescale.py
```

## 📁 Structure Rapide

```
T-DAT/
├── crypto_viz_backend/    # API Django REST
├── spark_jobs/            # Jobs Spark Streaming
├── database/              # Scripts SQL TimescaleDB
├── scripts/               # Scripts utilitaires
├── logs/                  # Logs des services
├── docker-compose.yml     # Orchestration Docker
└── .env                   # Configuration
```

## 🎯 Prochaines Étapes

1. **Créer un superuser Django** :
   ```bash
   cd crypto_viz_backend
   python manage.py createsuperuser
   ```

2. **Accéder à l'admin** : http://localhost:8000/admin/

3. **Configurer les cryptos** dans l'admin Django

4. **Développer le frontend** (React/Vue.js)

5. **Ajouter des tests** :
   ```bash
   python manage.py test
   ```

## 📚 Documentation Complète

Voir [README.md](./README.md) pour la documentation détaillée.

## 🆘 Besoin d'Aide?

- **Vérifier les logs** : `tail -f logs/*.log`
- **Health check** : `curl http://localhost:8000/api/v1/health/`
- **Tests connexion** : Exécuter les scripts dans `scripts/`
- **Docker status** : `docker compose ps`

---

**Note** : Si vous rencontrez des problèmes, vérifiez d'abord que :
1. Le serveur Kafka (20.199.136.163:9092) est accessible
2. Docker est démarré et fonctionnel
3. Les ports 15432, 6380 et 8000 sont libres
