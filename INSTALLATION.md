# 🚀 Guide d'Installation Complet - CRYPTO VIZ

Ce guide vous accompagne pas à pas dans l'installation complète du système CRYPTO VIZ.

## ✅ Prérequis

Avant de commencer, assurez-vous d'avoir installé :

### Obligatoire

- **Python 3.11+** : Backend Django et jobs Spark
  ```bash
  python3 --version
  ```

- **Docker & Docker Compose** : TimescaleDB et Redis
  ```bash
  docker --version
  docker compose version
  ```

- **Java 11+** : Requis pour Apache Spark
  ```bash
  java -version
  ```

- **Git** : Pour cloner le projet (si applicable)
  ```bash
  git --version
  ```

### Optionnel

- **Node.js** : Si vous développez le frontend
- **PostgreSQL client** : Pour accéder manuellement à TimescaleDB

---

## 📥 Étape 1 : Récupération du Projet

Si vous n'avez pas encore le projet :

```bash
# Naviguer vers le répertoire
cd /home/kevyn-odjo/Documents/T-DAT

# Vérifier le contenu
ls -la
```

Vous devriez voir :
- `crypto_viz_backend/`
- `spark_jobs/`
- `database/`
- `scripts/`
- `docker-compose.yml`
- Fichiers `.md` de documentation

---

## ⚙️ Étape 2 : Configuration Initiale

### 2.1 Créer le Fichier .env

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos configurations
nano .env
```

**Configurations minimales à vérifier** :

```bash
# Django
SECRET_KEY=votre-cle-secrete-unique-ici
DEBUG=True

# Kafka (devrait être correct par défaut)
KAFKA_SERVERS=20.199.136.163:9092

# TimescaleDB (ajuster si nécessaire)
TIMESCALE_DB_NAME=crypto_viz_ts
TIMESCALE_DB_USER=postgres
TIMESCALE_DB_PASSWORD=password
TIMESCALE_DB_HOST=localhost
TIMESCALE_DB_PORT=15432
```

### 2.2 Créer les Répertoires Nécessaires

```bash
# Répertoire de logs
mkdir -p logs

# Répertoire de checkpoints Spark
mkdir -p /tmp/spark_checkpoints
```

### 2.3 Rendre les Scripts Exécutables

```bash
chmod +x scripts/*.sh
```

---

## 🐳 Étape 3 : Installation Docker

### 3.1 Démarrer TimescaleDB et Redis

```bash
docker compose up -d timescaledb redis
```

**Vérification** :
```bash
# Voir les conteneurs actifs
docker compose ps

# Devrait afficher :
# - crypto_viz_timescaledb (port 15432)
# - crypto_viz_redis (port 6380)
```

### 3.2 Attendre le Démarrage (important!)

```bash
# Attendre 30 secondes pour que TimescaleDB soit prêt
sleep 30
```

**Alternative - Vérifier manuellement** :
```bash
docker logs crypto_viz_timescaledb | grep "database system is ready"
```

### 3.3 Initialiser TimescaleDB

```bash
# Exécuter le script SQL d'initialisation
docker exec -i crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts < database/timescaledb_setup.sql
```

**Vérification** :
```bash
# Tester la connexion
python3 scripts/test_timescale_connection.py
```

Vous devriez voir les hypertables créées :
- ticker_data
- trade_data
- article_data
- alert_data
- sentiment_data
- prediction_data

---

## 🐍 Étape 4 : Installation Backend Django

### 4.1 Créer l'Environnement Virtuel

```bash
cd crypto_viz_backend

# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 4.2 Installer les Dépendances

```bash
# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt
```

**Temps estimé** : 2-3 minutes

### 4.3 Configurer Django

```bash
# Effectuer les migrations SQLite (métadonnées)
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic --noinput
```

### 4.4 Créer un Superuser (optionnel mais recommandé)

```bash
python manage.py createsuperuser

# Suivre les instructions :
# - Username : admin
# - Email : admin@example.com
# - Password : ********
```

### 4.5 Tester Django

```bash
# Démarrer le serveur
python manage.py runserver 0.0.0.0:8000
```

**Ouvrir dans le navigateur** : http://localhost:8000/api/v1/health/

Vous devriez voir :
```json
{
  "status": "healthy",
  "service": "CRYPTO VIZ API",
  "version": "1.0.0"
}
```

**Arrêter le serveur** : `Ctrl+C`

---

## ⚡ Étape 5 : Installation Jobs Spark

### 5.1 Créer l'Environnement Virtuel

```bash
# Retour au répertoire principal
cd ..

# Aller dans spark_jobs
cd spark_jobs

# Créer l'environnement virtuel
python3 -m venv venv

# Activer
source venv/bin/activate
```

### 5.2 Installer les Dépendances Spark

```bash
# Mettre à jour pip
pip install --upgrade pip

# Installer PySpark et dépendances
pip install -r requirements.txt
```

**Temps estimé** : 3-5 minutes (PySpark est volumineux)

### 5.3 Tester la Connexion Kafka

```bash
# Retour au répertoire principal
cd ..

# Tester Kafka
python3 scripts/test_kafka_connection.py
```

**Résultat attendu** :
```
✓ Connexion établie au topic 'rawticker'
✓ Connexion établie au topic 'rawtrade'
...
```

---

## 🎉 Étape 6 : Démarrage Automatique (RECOMMANDÉ)

### Option A : Démarrage Automatique avec Script

```bash
# Démarrer tous les services en une commande
./scripts/start_all.sh
```

Ce script va :
1. ✅ Démarrer TimescaleDB et Redis (Docker)
2. ✅ Initialiser la base de données
3. ✅ Lancer Django API (port 8000)
4. ✅ Lancer Spark Ingestion Job
5. ✅ Lancer Spark Analytics Job

**Services actifs** :
- API Django : http://localhost:8000
- Admin Django : http://localhost:8000/admin
- TimescaleDB : localhost:15432
- Redis : localhost:6380

**Arrêter tous les services** :
```bash
./scripts/stop_all.sh
```

---

### Option B : Démarrage Manuel (Pour Debug)

**Terminal 1 - Django** :
```bash
cd crypto_viz_backend
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

**Terminal 2 - Spark Ingestion** :
```bash
cd spark_jobs
source venv/bin/activate
python kafka_to_timescale.py
```

**Terminal 3 - Spark Analytics** :
```bash
cd spark_jobs
source venv/bin/activate
python sentiment_prediction_job.py
```

**Arrêter** : `Ctrl+C` dans chaque terminal

---

## 🧪 Étape 7 : Vérification Complète

### 7.1 Vérifier l'API

```bash
# Health check
curl http://localhost:8000/api/v1/health/

# Liste des cryptos (vide au début)
curl http://localhost:8000/api/v1/config/crypto/
```

### 7.2 Vérifier TimescaleDB

```bash
python3 scripts/test_timescale_connection.py
```

Devrait afficher :
- ✅ Connexion établie
- ✅ Version PostgreSQL
- ✅ Version TimescaleDB
- ✅ Liste des hypertables
- ✅ Nombre d'enregistrements (0 au début)

### 7.3 Vérifier Kafka

```bash
python3 scripts/test_kafka_connection.py
```

Devrait afficher les messages des topics.

### 7.4 Vérifier les Logs

```bash
# Logs Django
tail -f logs/django.log

# Logs Spark
tail -f logs/spark_ingestion.log
tail -f logs/spark_analytics.log
```

---

## 📊 Étape 8 : Utilisation de l'API

### 8.1 Accéder à l'Admin Django

1. Ouvrir http://localhost:8000/admin/
2. Se connecter avec le superuser créé
3. Ajouter des configurations de cryptos

### 8.2 Tester les Endpoints

**Sentiment BTC (24h)** :
```bash
curl "http://localhost:8000/api/v1/sentiment/BTC/historique/?periode=24h"
```

**Prix ETH/USD (1h)** :
```bash
curl "http://localhost:8000/api/v1/ticker/ETH/USD/historique/?periode=1h"
```

**Articles récents** :
```bash
curl "http://localhost:8000/api/v1/article/historique/?periode=24h"
```

---

## 🐛 Résolution de Problèmes

### Problème : TimescaleDB ne démarre pas

**Solution** :
```bash
# Supprimer et recréer
docker compose down -v
docker compose up -d timescaledb redis
sleep 30
docker exec -i crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts < database/timescaledb_setup.sql
```

### Problème : Django - Erreur de module

**Solution** :
```bash
cd crypto_viz_backend
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Problème : Spark - Erreur Java

**Solution** :
```bash
# Vérifier Java
java -version

# Doit être >= 11
# Installer Java si nécessaire :
sudo apt install openjdk-11-jdk  # Ubuntu/Debian
```

### Problème : Kafka inaccessible

**Solution** :
```bash
# Vérifier la connectivité réseau
ping 20.199.136.163

# Vérifier le port
telnet 20.199.136.163 9092

# Si échec : vérifier firewall ou VPN
```

### Problème : Ports occupés

**Solution** :
```bash
# Vérifier qui utilise le port 8000
lsof -i :8000

# Tuer le processus si nécessaire
kill -9 <PID>
```

---

## 🔄 Commandes de Maintenance

### Redémarrer Tous les Services

```bash
./scripts/stop_all.sh
./scripts/start_all.sh
```

### Nettoyer les Logs

```bash
rm logs/*.log
```

### Nettoyer les Checkpoints Spark

```bash
rm -rf /tmp/spark_checkpoints/*
```

### Réinitialiser TimescaleDB

```bash
docker compose down -v
docker compose up -d timescaledb
sleep 30
docker exec -i crypto_viz_timescaledb psql -U postgres -d crypto_viz_ts < database/timescaledb_setup.sql
```

---

## 📚 Ressources Supplémentaires

- **[README.md](./README.md)** : Documentation complète
- **[QUICKSTART.md](./QUICKSTART.md)** : Démarrage rapide (5 min)
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** : Architecture détaillée
- **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** : Structure du projet

---

## ✅ Checklist d'Installation

- [ ] Python 3.11+ installé
- [ ] Docker et Docker Compose installés
- [ ] Java 11+ installé
- [ ] Fichier .env créé et configuré
- [ ] TimescaleDB et Redis démarrés (Docker)
- [ ] Base de données TimescaleDB initialisée
- [ ] Backend Django installé et testé
- [ ] Jobs Spark installés
- [ ] Connexion Kafka testée
- [ ] Tous les services démarrés avec `start_all.sh`
- [ ] API accessible sur http://localhost:8000
- [ ] Superuser Django créé

---

## 🎯 Prochaines Étapes

Après l'installation :

1. **Configurer les cryptos** dans l'admin Django
2. **Développer le frontend** (React/Vue.js)
3. **Ajouter des tests** unitaires
4. **Configurer le monitoring** (Prometheus/Grafana)
5. **Préparer le déploiement** en production

---

**Besoin d'aide ?**
- Vérifier les logs : `tail -f logs/*.log`
- Tester les connexions : Scripts dans `scripts/`
- Consulter la documentation : `README.md`

**Bonne utilisation de CRYPTO VIZ !** 🚀
