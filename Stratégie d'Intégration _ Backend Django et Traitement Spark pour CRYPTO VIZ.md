# Stratégie d'Intégration : Backend Django et Traitement Spark pour CRYPTO VIZ

## 1. Introduction

Ce document définit la stratégie d'intégration du serveur backend **Django** avec les résultats du traitement de données en temps réel effectué par **Apache Spark** pour le projet CRYPTO VIZ. Le backend Django servira principalement d'interface entre la Visionneuse Dynamique (Frontend) et les données d'analyse stockées.

L'utilisation de **SQLite** comme base de données est prise en compte, mais ses limitations dans un contexte de Big Data en temps réel sont soulignées, menant à une architecture où SQLite n'est pas la source principale des données de séries temporelles.

## 2. Rôle de Django dans l'Architecture CRYPTO VIZ

Dans l'architecture de traitement de flux, Django n'est **pas** le composant chargé du traitement des données brutes (rôle de Spark). Son rôle est de servir de **couche d'API** pour le frontend.

| Composant | Rôle Principal | Outils Recommandés |
| :--- | :--- | :--- |
| **Générateur d'Analyses** | Traitement de flux (NLP, ML). | Apache Spark Structured Streaming |
| **Base de Données (Séries Temporelles)** | Stockage des résultats d'analyse pour la dimension temporelle. | **Externe à Django** (ex: TimescaleDB, InfluxDB) |
| **Backend Django** | Fournir des API REST pour les données historiques et gérer la communication en temps réel. | Django REST Framework, Django Channels |
| **Visionneuse Dynamique** | Affichage des données. | Frontend (React/Vue/etc.) |

## 3. Stratégie d'Utilisation de SQLite

L'utilisation de **SQLite** est possible, mais elle doit être strictement limitée en raison de ses contraintes inhérentes, notamment le manque de support pour la **concurrence en écriture** et ses performances limitées pour les requêtes complexes sur de grands volumes de données [1] [2].

| Utilisation Recommandée (avec SQLite) | Utilisation Déconseillée (Nécessite une DB Externe) |
| :--- | :--- |
| **Métadonnées du Projet :** Stockage des configurations, des utilisateurs (si authentification ajoutée), des paramètres de visualisation. | **Données de Séries Temporelles :** Stockage des analyses de sentiment et des prédictions générées par Spark. |
| **Cache de Données :** Stockage temporaire de résultats agrégés pour accélérer les requêtes fréquentes. | **Opérations d'Écriture Concurrentes :** Spark écrit en continu les résultats d'analyse. |

**Conclusion sur SQLite :** SQLite sera utilisé pour les besoins standard de Django (sessions, utilisateurs, configurations), mais une **Base de Données de Séries Temporelles (DB-TS)** externe est **impérative** pour stocker les résultats d'analyse de Spark.

## 4. Intégration des Résultats de Spark et de la Base de Données Externe

Le flux de données entre Spark et Django doit être indirect, via la DB-TS :

1.  **Spark** (Générateur d'Analyses) écrit en continu les résultats d'analyse et de prédiction dans la **DB-TS**.
2.  **Django** interroge la **DB-TS** via une connexion dédiée (sans utiliser l'ORM de Django, ou en utilisant un ORM adapté si la DB-TS le permet) pour récupérer les données historiques demandées par le frontend.

### 4.1. API REST pour les Données Historiques

Django, via le **Django REST Framework (DRF)**, exposera des points de terminaison (endpoints) pour la Visionneuse :

*   `/api/v1/sentiment/btc/historique?periode=24h` : Récupère l'historique du sentiment pour Bitcoin sur les dernières 24 heures.
*   `/api/v1/prediction/eth/historique?date_debut=...` : Récupère les prédictions passées pour Ethereum.

Ces vues Django se connecteront à la DB-TS pour exécuter des requêtes optimisées pour les séries temporelles.

## 5. Gestion de la Communication en Temps Réel avec Django Channels

L'exigence de la Visionneuse Dynamique est de se mettre à jour en temps réel. Bien que le document d'avancement ait déjà mentionné une API WebSocket (`ws://20.199.136.163:8000/ws/...`), Django peut servir de **WebSocket Gateway** alternatif ou complémentaire en utilisant **Django Channels** [3].

### 5.1. Rôle de Django Channels

Django Channels permet à Django de gérer les protocoles non-HTTP, y compris les WebSockets.

| Flux de Données en Temps Réel | Stratégie d'Implémentation |
| :--- | :--- |
| **Mises à Jour Immédiates :** Les dernières analyses et prédictions de Spark. | **Option 1 (Recommandée) :** Le service WebSocket existant (celui qui lit Kafka) est conservé. Django n'intervient pas dans ce flux direct. |
| **Option 2 (Alternative) :** Un *worker* Django Channels (Consumer) s'abonne aux topics Kafka de résultats (`analyzed-sentiment`, `predicted-price`) et retransmet les messages aux clients WebSocket connectés via le *Channel Layer* (ex: Redis). |

**Recommandation :** Si le service WebSocket existant est performant, Django devrait se concentrer sur les API REST pour les données historiques. Si une logique métier supplémentaire est nécessaire avant la diffusion en temps réel, l'Option 2 avec Django Channels est préférable.

## 6. Résumé de l'Architecture d'Intégration

| Composant | Technologie | Rôle dans l'Intégration |
| :--- | :--- | :--- |
| **Traitement** | Apache Spark | Génère les analyses et écrit dans la DB-TS. |
| **Stockage** | DB-TS Externe | Source de vérité pour les données de séries temporelles. |
| **Backend** | Django + DRF | Fournit les API REST pour les données historiques (lecture de la DB-TS). |
| **Temps Réel** | API WebSocket Externe | Diffuse les mises à jour en direct (lecture de Kafka). |
| **Métadonnées** | Django + SQLite | Stocke les configurations et les données non critiques. |

## 7. Prochaines Étapes

1.  **Sélection de la DB-TS :** Choisir la base de données de séries temporelles (ex: TimescaleDB, InfluxDB) et définir son schéma de données.
2.  **Implémentation Spark Sink :** Configurer le job Spark Structured Streaming pour écrire les résultats dans la DB-TS.
3.  **Développement de l'API Django :** Créer les modèles Django pour les métadonnées (avec SQLite) et les vues DRF pour interroger la DB-TS.

