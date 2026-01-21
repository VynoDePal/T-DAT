#!/usr/bin/env python3
"""
Script pour tester la connexion à TimescaleDB et vérifier les tables.
"""
import psycopg2
import os
from tabulate import tabulate

# Configuration (à ajuster selon votre .env)
DB_CONFIG = {
    'host': os.environ.get('TIMESCALE_DB_HOST', 'localhost'),
    'port': os.environ.get('TIMESCALE_DB_PORT', '15432'),
    'database': os.environ.get('TIMESCALE_DB_NAME', 'crypto_viz_ts'),
    'user': os.environ.get('TIMESCALE_DB_USER', 'postgres'),
    'password': os.environ.get('TIMESCALE_DB_PASSWORD', 'password'),
}

def test_connection():
    """Teste la connexion à TimescaleDB."""
    print("\n" + "="*60)
    print("CRYPTO VIZ - Test de Connexion TimescaleDB")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  Host:     {DB_CONFIG['host']}")
    print(f"  Port:     {DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['database']}")
    print(f"  User:     {DB_CONFIG['user']}")
    print()
    
    try:
        # Connexion
        print("Connexion à TimescaleDB...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✓ Connexion établie!")
        
        # Vérifier la version de PostgreSQL
        cursor.execute("SELECT version();")
        pg_version = cursor.fetchone()[0]
        print(f"\n✓ PostgreSQL: {pg_version.split(',')[0]}")
        
        # Vérifier TimescaleDB
        cursor.execute("SELECT extversion FROM pg_extension WHERE extname='timescaledb';")
        result = cursor.fetchone()
        if result:
            print(f"✓ TimescaleDB: version {result[0]}")
        else:
            print("⚠ Extension TimescaleDB non installée!")
        
        # Lister les hypertables
        print("\n" + "-"*60)
        print("HYPERTABLES CONFIGURÉES")
        print("-"*60)
        cursor.execute("""
            SELECT hypertable_name, num_dimensions, num_chunks
            FROM timescaledb_information.hypertables
            ORDER BY hypertable_name;
        """)
        hypertables = cursor.fetchall()
        
        if hypertables:
            print(tabulate(
                hypertables,
                headers=['Table', 'Dimensions', 'Chunks'],
                tablefmt='grid'
            ))
        else:
            print("⚠ Aucune hypertable trouvée. Exécutez le script timescaledb_setup.sql")
        
        # Compter les enregistrements dans chaque table
        print("\n" + "-"*60)
        print("NOMBRE D'ENREGISTREMENTS PAR TABLE")
        print("-"*60)
        
        tables = [
            'ticker_data',
            'trade_data',
            'article_data',
            'alert_data',
            'sentiment_data',
            'prediction_data'
        ]
        
        counts = []
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                counts.append([table, f"{count:,}"])
            except Exception as e:
                counts.append([table, f"Erreur: {e}"])
        
        print(tabulate(counts, headers=['Table', 'Enregistrements'], tablefmt='grid'))
        
        # Vérifier les vues matérialisées
        print("\n" + "-"*60)
        print("VUES MATÉRIALISÉES")
        print("-"*60)
        cursor.execute("""
            SELECT view_name 
            FROM timescaledb_information.continuous_aggregates
            ORDER BY view_name;
        """)
        views = cursor.fetchall()
        
        if views:
            for view in views:
                print(f"  • {view[0]}")
        else:
            print("⚠ Aucune vue matérialisée trouvée")
        
        # Fermer la connexion
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✓ Test terminé avec succès!")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Erreur: {e}\n")
        return False


if __name__ == "__main__":
    import sys
    success = test_connection()
    sys.exit(0 if success else 1)
