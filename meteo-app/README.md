# meteo-app

Application Android Flutter qui affiche une météo **composite** : pour chaque ville et chaque horizon (J+1 à J+7), chaque métrique (température, pluie, vent) provient du fournisseur le mieux classé dans le benchmark.

## Fonctionnalités

- Sélection parmi toutes les villes du benchmark
- **Aujourd’hui** : température actuelle, ressenti, min/max du jour, risque de pluie
- **J+1 … J+7** : prévisions journalières issues des meilleures sources par métrique
- Graphique horaire température + bandeau pluie
- Attribution des sources (tap sur la barre d’info)

## Prérequis

- Flutter SDK 3.12+
- Android SDK + émulateur (ou appareil USB)
- Projet Supabase du benchmark avec données collectées

### Supabase : politiques RLS

Exécutez `supabase/rls_read_anon.sql` dans le SQL Editor Supabase, ou :

```powershell
cd weather-benchmark/scripts
python apply_rls_anon.py
```

### Secrets (automatique)

Les identifiants Supabase sont stockés dans `lib/config/secrets.local.dart` (**gitignored**).

Génération (une fois, ou après changement de projet) :

```powershell
cd meteo-app
python tool/sync_secrets.py
```

Le script lit `weather-benchmark/scripts/.env` et, si besoin, récupère la clé publishable via Supabase CLI (`npx supabase login`).

## Lancement Android

```powershell
cd meteo-app
.\run_android.ps1
```

Ce script :
1. génère `secrets.local.dart` si absent ;
2. démarre l’émulateur `android-15` si aucun appareil Android n’est connecté ;
3. lance `flutter run`.

Lancement manuel :

```powershell
flutter emulators --launch android-15
flutter run -d android
```

> `flutter run` seul échoue sur Windows sans émulateur : le projet cible **Android uniquement** (pas Windows desktop).

## Architecture

| Couche | Rôle |
|--------|------|
| `SupabaseRepository` | Villes, scores, prévisions journalières |
| `BenchmarkResolver` | Meilleur fournisseur par métrique / ville / horizon |
| `OpenMeteoService` | Temps actuel + horaire (OM / MF) ou synthèse daily |
| `WeatherOrchestrator` | Assemble un `DayBundle` pour l’UI |

## Sécurité

- La clé **publishable** Supabase est prévue pour les apps clientes ; l’accès est limité par les **politiques RLS** (lecture seule).
- Ne jamais embarquer la clé `service_role` dans l’app.
- `secrets.local.dart` reste hors git ; en cas de clone frais, relancer `python tool/sync_secrets.py`.
