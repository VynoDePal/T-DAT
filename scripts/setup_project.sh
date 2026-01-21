#!/bin/bash

# Script d'installation initiale du projet CRYPTO VIZ

set -e

echo "========================================="
echo "CRYPTO VIZ - Installation Initiale"
echo "========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

cd "$(dirname "$0")/.."

# 1. Vérifier les prérequis
log_info "Vérification des prérequis..."

if ! command -v python3 &> /dev/null; then
    log_warn "Python 3 n'est pas installé!"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_warn "Docker n'est pas installé!"
    exit 1
fi

if ! command -v java &> /dev/null; then
    log_warn "Java n'est pas installé (requis pour Spark)!"
    exit 1
fi

log_info "✓ Prérequis validés"

# 2. Créer les répertoires nécessaires
log_info "Création des répertoires..."
mkdir -p logs
mkdir -p /tmp/spark_checkpoints

# 3. Configuration .env
if [ ! -f ".env" ]; then
    log_info "Création du fichier .env..."
    cp .env.example .env
    log_warn "⚠ N'oubliez pas de configurer .env avec vos paramètres!"
else
    log_info "✓ Fichier .env déjà existant"
fi

# 4. Rendre les scripts exécutables
log_info "Configuration des permissions des scripts..."
chmod +x scripts/*.sh

# 5. Installation Django
log_info "Installation de l'environnement Django..."
cd crypto_viz_backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

log_info "✓ Django installé"

# 6. Installation Spark
log_info "Installation de l'environnement Spark..."
cd ../spark_jobs

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

log_info "✓ Spark installé"

cd ..

# 7. Résumé
echo ""
echo "========================================="
echo -e "${GREEN}✓ Installation terminée!${NC}"
echo "========================================="
echo ""
echo "Prochaines étapes:"
echo ""
echo "  1. Configurer le fichier .env"
echo "     nano .env"
echo ""
echo "  2. Démarrer tous les services:"
echo "     ./scripts/start_all.sh"
echo ""
echo "  3. Créer un superuser Django:"
echo "     cd crypto_viz_backend"
echo "     source venv/bin/activate"
echo "     python manage.py createsuperuser"
echo ""
echo "  4. Accéder à l'API:"
echo "     http://localhost:8000/api/v1/health/"
echo ""
echo "Pour plus d'informations, voir:"
echo "  - README.md"
echo "  - QUICKSTART.md"
echo ""
