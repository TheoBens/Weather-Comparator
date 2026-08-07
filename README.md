# Weather Comparator

[Link to the website](https://weather-comparator-lime.vercel.app/)

Bench qui compare plusieurs APIs météo (précision température, vent, pluie) sur un panel de villes françaises.

## Stack

| Rôle | Technologie |
|------|-------------|
| **Frontend (site web)** | [Next.js](https://nextjs.org) 16 + [React](https://react.dev) + [Tailwind CSS](https://tailwindcss.com) — app dans `weather-benchmark/dashboard/` |
| **Hébergement du site** | [Vercel](https://vercel.com) (déploiement depuis GitHub) |
| **« Backend » du site** | Pas de serveur API séparé : Next.js lit **directement** PostgreSQL au rendu serveur (`postgres.js`, page `force-dynamic`) |
| **Base de données** | [Supabase](https://supabase.com) (PostgreSQL) — prévisions, observations, scores |
| **Collecte & calculs** | Python 3 (`weather-benchmark/scripts/`) : collecte prévisions/observations, calcul des scores (MAE, précision pluie, etc.) |
| **Automatisation** | [GitHub Actions](https://github.com/features/actions) (cron quotidien : collecte → scores en base) |

Le site se met à jour **sans redeploy** : les Actions alimentent Supabase, le dashboard relit la base à chaque visite.

## Dashboard en local

Depuis la racine du dépôt :

```bash
cd weather-benchmark/dashboard
npm install    # une seule fois
npm run dev
```

Ouvrir [http://localhost:3000](http://localhost:3000).

Configurer `weather-benchmark/dashboard/.env.local` avec les **mêmes** variables Postgres que `weather-benchmark/scripts/.env` (`POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, etc.). Redémarre `npm run dev` après modification.

Mise en ligne sur Vercel : voir `weather-benchmark/dashboard/DEPLOY_VERCEL.md`.

## APIs météo comparées

- Open-Meteo
- Météo-France (modèle via Open-Meteo)
- WeatherAPI
- OpenWeatherMap
- Tomorrow.io
- Visual Crossing

## Dépôt

- `weather-benchmark/dashboard/` — site comparatif (Next.js)
- `weather-benchmark/scripts/` — pipeline Python + `.env`
- `weather-benchmark/supabase/` — schéma SQL
- `.github/workflows/` — cron GitHub Actions
