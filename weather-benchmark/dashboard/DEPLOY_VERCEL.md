# Déployer le dashboard sur Vercel (gratuit)

Le site lit **Supabase en direct** à chaque visite. Les mises à jour viennent de **GitHub Actions** (cron) qui remplit la base — **pas besoin de redéployer Vercel** quand seules les données changent.

## Prérequis

- Repo sur **GitHub** (ex. `Weather-Comparator`) avec le code poussé sur `main`.
- Projet **Supabase** déjà utilisé par `weather-benchmark/scripts` (mêmes identifiants DB).
- Le workflow `.github/workflows/weather-daily.yml` tourne (ou au moins une fois `compute_scores.py`) pour avoir des lignes dans `forecast_scores`.

## 1. Compte et import du projet

1. Va sur [https://vercel.com](https://vercel.com) → connexion avec **GitHub**.
2. **Add New… → Project** → choisis ton dépôt.
3. **Configure Project** — réglages importants :

   | Champ | Valeur |
   |--------|--------|
   | **Framework Preset** | Next.js (détecté auto) |
   | **Root Directory** | `weather-benchmark/dashboard` ← **obligatoire** (sinon Vercel build la racine du repo et échoue) |
   | **Build Command** | `npm run build` (défaut) |
   | **Output Directory** | (laisser vide / défaut Next) |
   | **Install Command** | `npm install` (défaut) |

4. **Ne clique pas encore sur Deploy** — configure d’abord les variables (étape 2).

## 2. Variables d’environnement (Production)

Dans **Environment Variables**, ajoute les mêmes valeurs que dans `dashboard/.env.local` (copie depuis `scripts/.env` qui fonctionne déjà).

### Option A — recommandée (pooler Supabase)

| Nom | Exemple / remarque |
|-----|-------------------|
| `POSTGRES_HOST` | `aws-0-eu-central-1.pooler.supabase.com` (Session pooler, Supabase → Database) |
| `POSTGRES_USER` | `postgres.abcdefghij` (**pas** `postgres` seul sur le pooler) |
| `POSTGRES_PASSWORD` | Mot de passe **Database** du projet |
| `POSTGRES_DB` | `postgres` |
| `POSTGRES_PORT` | `5432` (souvent 5432 pour Session pooler) |

Coche **Production** (et **Preview** si tu veux les previews de PR identiques).

**Mot de passe avec `#` ou `;`** : colle la valeur telle quelle dans l’UI Vercel (pas de commentaire `#` comme dans un fichier `.env`).

### Option B — une seule URI

| Nom | Valeur |
|-----|--------|
| `DATABASE_URL` | URI **Session pooler** copiée depuis Supabase, user = `postgres.<ref>` |

Si tu utilises l’option A, **supprime complètement** `DATABASE_URL` sur Vercel (Settings → Environment Variables → ⋮ → Remove).  
Sinon Vercel peut encore l’avoir en prod alors que tu crois n’utiliser que `POSTGRES_*`.

### Mot de passe avec `#` (très fréquent)

- **Sur Vercel** : colle le mot de passe **tel quel** dans `POSTGRES_PASSWORD` (pas de guillemets, pas de `#` qui coupe — l’UI n’est pas un fichier `.env`).
- **Ne mets pas** une `DATABASE_URL` du type `postgresql://postgres:abc#def@host` : le `#` tronque le mot de passe et Postgres voit l’utilisateur `postgres` → erreur *password authentication failed for user "postgres"*.
- En local, dans `.env` / `.env.local`, utilise plutôt :  
  `POSTGRES_PASSWORD="ton#motDePasse"`  
  et laisse `DATABASE_URL` commentée ou absente.

### Secrets API météo

**Pas nécessaires** sur Vercel : le dashboard ne appelle que Postgres. Les clés `WEATHERAPI_KEY`, etc. restent dans **GitHub Actions secrets** uniquement.

## 3. Premier déploiement

1. **Deploy**.
2. Attends la fin du build (log `npm run build` doit réussir comme en local).
3. Ouvre l’URL fournie (`https://ton-projet.vercel.app`).

Si la page affiche « Aucun score en base », la DB est vide ou le workflow n’a pas encore calculé les scores — ce n’est pas un problème Vercel.

## 4. Mises à jour automatiques

| Événement | Effet |
|-----------|--------|
| Push sur `main` qui modifie `weather-benchmark/dashboard/**` | Vercel **rebuild** le site (nouveau code UI). |
| Cron GitHub Actions (collecte + scores) | Données Supabase mises à jour → **rafraîchir la page** suffit. |

Tu peux désactiver les deploys auto dans Vercel → Project → Settings → Git si tu préfères déployer à la main.

## 5. Domaine personnalisé (optionnel)

Vercel → Project → **Settings → Domains** → ajoute un sous-domaine (ex. `meteo.tondomaine.fr`) et suis les instructions DNS.

## 6. Vérifications si ça échoue

### Build échoue (« Cannot find package.json »)

→ **Root Directory** n’est pas `weather-benchmark/dashboard`.

### « Configuration Postgres » / page ambre

→ Aucune variable DB sur Vercel, ou `POSTGRES_PASSWORD` vide.

### « password authentication failed » / « user postgres »

→ Sur pooler : `POSTGRES_USER=postgres.<ref_projet>`, pas `postgres`.  
→ Mot de passe = celui de **Database password** Supabase (réinitialisable dans le dashboard Supabase).

### « Tenant or user not found »

→ Mauvaise combinaison host / user / région pooler — recopie le bloc **Session pooler** depuis Supabase.

### Page vide mais pas d’erreur SQL

→ Table `forecast_scores` vide : lance le workflow Actions ou `compute_scores.py` / `compute_fair_scores.py` en local.

### Build OK, erreur seulement en production au chargement

→ Vercel **serverless** : connexion Postgres OK si pooler + SSL ; évite l’hôte direct `db.xxx.supabase.co` si ton projet n’accepte que le pooler en serverless.

## 7. Alternative : CLI Vercel

```bash
cd weather-benchmark/dashboard
npm i -g vercel
vercel login
vercel link
vercel env add POSTGRES_HOST
vercel env add POSTGRES_USER
vercel env add POSTGRES_PASSWORD
vercel env add POSTGRES_DB
vercel env add POSTGRES_PORT
vercel --prod
```

Même règles pour le répertoire courant (`dashboard/`) et les variables.

## Récap architecture

```
GitHub Actions (cron)  →  Supabase Postgres  ←  Vercel (Next.js, force-dynamic)
     collect + scores              forecast_scores              lecture à la visite
```
