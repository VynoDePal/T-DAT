# 🔧 Guide de Dépannage - CRYPTO VIZ

## Problème : Erreur psycopg2-binary avec Python 3.13

### ❌ Erreur rencontrée

```
fatal error: libpq-fe.h: Aucun fichier ou dossier de ce nom
ERROR: Failed building wheel for psycopg2-binary
```

### 🔍 Cause du problème

**Python 3.13** est très récent et `psycopg2-binary==2.9.9` n'a pas de wheels pré-compilés pour cette version. Le système essaie donc de compiler depuis la source, mais il manque les headers PostgreSQL.

### ✅ Solutions

#### Solution 1 : Mettre à jour psycopg2-binary (RECOMMANDÉ) ✨

**Avantage** : Simple et rapide, pas de dépendances système supplémentaires

La version `2.9.11` inclut des wheels pré-compilés pour Python 3.13.

```bash
# Les fichiers requirements.txt ont déjà été mis à jour vers 2.9.11
cd /home/kevyn-odjo/Documents/T-DAT

# Relancer l'installation
./scripts/setup_project.sh
```

#### Solution 2 : Installer les dépendances PostgreSQL

**Avantage** : Permet de compiler depuis la source (utile pour des versions spécifiques)

```bash
# Installer les headers PostgreSQL
sudo apt-get update
sudo apt-get install -y libpq-dev python3-dev

# Puis relancer l'installation
cd /home/kevyn-odjo/Documents/T-DAT
./scripts/setup_project.sh
```

#### Solution 3 : Installation manuelle dans l'environnement virtuel

```bash
cd /home/kevyn-odjo/Documents/T-DAT/crypto_viz_backend
source venv/bin/activate

# Installer psycopg2-binary 2.9.11 directement
pip install psycopg2-binary==2.9.11

# Puis installer le reste
pip install -r requirements.txt
```

#### Solution 4 : Utiliser psycopg3 (alternative moderne)

**Note** : Nécessite des modifications du code

`psycopg` (version 3) est le successeur moderne de `psycopg2` avec un meilleur support Python 3.13.

```bash
# Modifier requirements.txt
# Remplacer psycopg2-binary par psycopg[binary]

# Dans requirements.txt:
psycopg[binary]==3.1.19
psycopg[pool]==3.1.19
```

**Modifications de code nécessaires** :

```python
# Ancien (psycopg2):
import psycopg2
from psycopg2.extras import RealDictCursor

# Nouveau (psycopg3):
import psycopg
from psycopg.rows import dict_row
```

---

## Autres Problèmes Courants

### Erreur : "Port 15432 or 6380 already in use"

**Cause** : Un autre service utilise les ports Docker

**Solutions** :

```bash
# Vérifier quel processus utilise le port
sudo lsof -i :15432
sudo lsof -i :6380

# Si nécessaire, changer les ports dans docker-compose.yml
ports:
  - "15433:5432"  # TimescaleDB sur port externe différent
  - "6381:6379"  # Redis sur port externe différent
```

**Note** : Les ports Docker sont configurés sur 15432/6380 pour éviter les conflits avec PostgreSQL/Redis locaux.

### Erreur : "Port 8000 already in use"

**Cause** : Un autre serveur web utilise le port 8000

**Solutions** :

```bash
# Trouver le processus
lsof -i :8000

# Tuer le processus
kill -9 <PID>

# Ou utiliser un autre port
python manage.py runserver 0.0.0.0:8001
```

### Erreur : "Kafka connection timeout"

**Cause** : Le serveur Kafka n'est pas accessible

**Solutions** :

```bash
# Tester la connectivité
ping 20.199.136.163

# Tester le port Kafka
telnet 20.199.136.163 9092
# ou
nc -zv 20.199.136.163 9092

# Vérifier avec le script de test
python3 scripts/test_kafka_connection.py
```

**Causes possibles** :
- Firewall bloquant le port 9092
- VPN requis pour accéder au serveur
- Serveur Kafka hors ligne

### Erreur : "TimescaleDB connection refused"

**Cause** : TimescaleDB n'est pas démarré ou pas prêt

**Solutions** :

```bash
# Vérifier l'état des conteneurs
docker compose ps

# Redémarrer TimescaleDB
docker compose restart timescaledb

# Voir les logs
docker logs crypto_viz_timescaledb

# Attendre que la base soit prête
docker exec crypto_viz_timescaledb pg_isready -U postgres
```

### Erreur : Java non trouvé (pour Spark)

**Cause** : Java n'est pas installé ou pas dans le PATH

**Solutions** :

```bash
# Vérifier Java
java -version

# Installer Java 11 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk

# Installer Java 11 (Fedora/RHEL)
sudo dnf install java-11-openjdk-devel

# Définir JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
```

### Erreur : "ModuleNotFoundError: No module named 'pyspark'"

**Cause** : Environnement virtuel non activé ou dépendances non installées

**Solutions** :

```bash
cd /home/kevyn-odjo/Documents/T-DAT/spark_jobs

# Activer l'environnement virtuel
source venv/bin/activate

# Réinstaller les dépendances
pip install -r requirements.txt
```

### Erreur : Django migrations échouent

**Cause** : Base de données corrompue ou migrations conflictuelles

**Solutions** :

```bash
cd crypto_viz_backend
source venv/bin/activate

# Supprimer la base SQLite
rm db.sqlite3

# Supprimer les fichiers de migration (sauf __init__.py)
find api/migrations -name "*.py" ! -name "__init__.py" -delete

# Recréer les migrations
python manage.py makemigrations
python manage.py migrate
```

### Erreur : "Docker daemon not running"

**Cause** : Docker n'est pas démarré

**Solutions** :

```bash
# Démarrer Docker (Linux)
sudo systemctl start docker

# Activer Docker au démarrage
sudo systemctl enable docker

# Vérifier l'état
sudo systemctl status docker
```

### Erreur : Permissions insuffisantes pour Docker

**Cause** : L'utilisateur n'est pas dans le groupe docker

**Solutions** :

```bash
# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Se déconnecter et se reconnecter pour appliquer

# Ou redémarrer la session
newgrp docker

# Vérifier
docker ps
```

### Erreur : Spark "OutOfMemoryError"

**Cause** : Mémoire insuffisante allouée à Spark

**Solutions** :

```bash
# Modifier la configuration Spark dans config.py
# Ajouter ces options :

spark = SparkSession.builder \
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "50") \
    .getOrCreate()
```

### Logs pour le Debugging

```bash
# Logs Django
tail -f /home/kevyn-odjo/Documents/T-DAT/logs/django.log

# Logs Spark Ingestion
tail -f /home/kevyn-odjo/Documents/T-DAT/logs/spark_ingestion.log

# Logs Spark Analytics
tail -f /home/kevyn-odjo/Documents/T-DAT/logs/spark_analytics.log

# Logs TimescaleDB
docker logs -f crypto_viz_timescaledb

# Logs Redis
docker logs -f crypto_viz_redis
```

### Nettoyage Complet (dernier recours)

```bash
cd /home/kevyn-odjo/Documents/T-DAT

# Arrêter tous les services
./scripts/stop_all.sh

# Supprimer les environnements virtuels
rm -rf crypto_viz_backend/venv
rm -rf spark_jobs/venv

# Supprimer la base SQLite
rm -rf crypto_viz_backend/db.sqlite3

# Supprimer les volumes Docker
docker compose down -v

# Supprimer les checkpoints Spark
rm -rf /tmp/spark_checkpoints/*

# Supprimer les logs
rm -rf logs/*.log logs/*.pid

# Réinstaller
./scripts/setup_project.sh
```

---

## 📞 Obtenir de l'Aide

### Avant de demander de l'aide

1. **Vérifier les logs** (voir section ci-dessus)
2. **Tester les connexions** :
   ```bash
   python3 scripts/test_kafka_connection.py
   python3 scripts/test_timescale_connection.py
   curl http://localhost:8000/api/v1/health/
   ```
3. **Vérifier l'état des services** :
   ```bash
   docker compose ps
   ps aux | grep python
   ```

### Informations utiles à fournir

- Version de Python : `python3 --version`
- Version de Docker : `docker --version`
- Version de Java : `java -version`
- Système d'exploitation : `uname -a`
- Logs d'erreur complets
- Commandes exécutées avant l'erreur

---

## ✅ Checklist de Vérification

Avant de démarrer le projet, vérifier :

- [ ] Python 3.11+ installé
- [ ] Docker installé et démarré
- [ ] Java 11+ installé
- [ ] Ports 15432, 6380, 8000 disponibles
- [ ] Serveur Kafka accessible (20.199.136.163:9092)
- [ ] Fichier .env configuré
- [ ] Dépendances Python installées (venv actif)
- [ ] TimescaleDB initialisé

---

**Pour plus d'informations** :
- [README.md](./README.md)
- [INSTALLATION.md](./INSTALLATION.md)
- [QUICKSTART.md](./QUICKSTART.md)
