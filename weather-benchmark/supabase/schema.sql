-- Comparateur météo — schéma PostgreSQL (Supabase)
-- Horizons : lead_day 1..7 = J+1 .. J+7 (jour civil cible en UTC ou fuseau fixe)

-- (Optionnel : PostGIS si analyses spatiales)
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------------------
-- Référentiels
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS cities (
  id         SERIAL PRIMARY KEY,
  slug       TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL,
  country    TEXT NOT NULL DEFAULT 'FR',
  latitude   DOUBLE PRECISION NOT NULL,
  longitude  DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS providers (
  id    SERIAL PRIMARY KEY,
  code  TEXT NOT NULL UNIQUE,  -- ex: open_meteo, meteo_france, openweathermap
  name  TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Données brutes
-- ---------------------------------------------------------------------------

-- Une exécution du job de collecte (permet de relier prévisions au même run).
CREATE TABLE IF NOT EXISTS ingest_runs (
  id           BIGSERIAL PRIMARY KEY,
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ,
  source       TEXT NOT NULL DEFAULT 'github_actions',
  git_sha      TEXT,
  notes        TEXT
);

-- Prévisions horaires ou journalières : une ligne = un instant cible pour une ville et un fournisseur.
CREATE TABLE IF NOT EXISTS forecasts (
  id                 BIGSERIAL PRIMARY KEY,
  ingest_run_id      BIGINT REFERENCES ingest_runs(id) ON DELETE SET NULL,
  provider_id        INT NOT NULL REFERENCES providers(id),
  city_id            INT NOT NULL REFERENCES cities(id),
  issued_at          TIMESTAMPTZ NOT NULL,  -- moment de la prévision (run API)
  valid_time         TIMESTAMPTZ NOT NULL,  -- instant ou début de la période prévue
  lead_days          SMALLINT NOT NULL CHECK (lead_days >= 1 AND lead_days <= 7),
  time_step          TEXT NOT NULL DEFAULT 'daily',  -- daily | hourly
  -- Variables comparables
  temp_max_c         DOUBLE PRECISION,
  temp_min_c         DOUBLE PRECISION,
  temp_mean_c        DOUBLE PRECISION,
  wind_speed_ms      DOUBLE PRECISION,
  wind_gust_ms       DOUBLE PRECISION,
  wind_dir_deg       DOUBLE PRECISION,
  precip_prob        DOUBLE PRECISION,      -- 0..100 ou 0..1 selon source (normaliser en amont)
  precip_amount_mm   DOUBLE PRECISION,
  cloud_cover_pct    DOUBLE PRECISION,
  weather_code       INT,                   -- code météo unifié si disponible
  raw                JSONB                  -- payload brut pour debug
);

CREATE INDEX IF NOT EXISTS idx_forecasts_lookup
  ON forecasts (provider_id, city_id, valid_time, lead_days);
CREATE INDEX IF NOT EXISTS idx_forecasts_issued
  ON forecasts (issued_at);

-- Observations « réalisées » (agrégées journalières par ville).
CREATE TABLE IF NOT EXISTS observations (
  id               BIGSERIAL PRIMARY KEY,
  city_id          INT NOT NULL REFERENCES cities(id),
  obs_date         DATE NOT NULL,
  temp_max_c       DOUBLE PRECISION,
  temp_min_c       DOUBLE PRECISION,
  temp_mean_c      DOUBLE PRECISION,
  wind_speed_max_ms DOUBLE PRECISION,
  wind_dir_deg     DOUBLE PRECISION,
  precip_sum_mm    DOUBLE PRECISION,
  sunshine_hours   DOUBLE PRECISION,
  source           TEXT NOT NULL,           -- ex: meteostat, open_meteo_archive
  raw              JSONB,
  UNIQUE (city_id, obs_date, source)
);

CREATE INDEX IF NOT EXISTS idx_obs_city_date ON observations (city_id, obs_date);

-- ---------------------------------------------------------------------------
-- Scores (calculés hors ligne ou après mise à jour des obs)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS forecast_scores (
  id                    BIGSERIAL PRIMARY KEY,
  provider_id           INT NOT NULL REFERENCES providers(id),
  city_id               INT NOT NULL REFERENCES cities(id),
  horizon_days          SMALLINT NOT NULL CHECK (horizon_days >= 1 AND horizon_days <= 7),
  score_window_start    DATE NOT NULL,
  score_window_end      DATE NOT NULL,
  -- Métriques (null si pas assez de points)
  n_samples             INT NOT NULL DEFAULT 0,
  mae_temp_c            DOUBLE PRECISION,
  rmse_temp_c           DOUBLE PRECISION,
  mae_wind_ms           DOUBLE PRECISION,
  -- Pluie : classification (ex: seuil 0.1 mm) + régression quantité
  rain_binary_accuracy  DOUBLE PRECISION,
  rain_mae_mm           DOUBLE PRECISION,
  precip_prob_brier     DOUBLE PRECISION,  -- Brier score (plus bas = mieux)
  computed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider_id, city_id, horizon_days, score_window_start, score_window_end)
);

CREATE INDEX IF NOT EXISTS idx_scores_leaderboard
  ON forecast_scores (horizon_days, score_window_start, provider_id);

-- ---------------------------------------------------------------------------
-- Données initiales : villes FR (coordonnées approximatives centre-ville)
-- ---------------------------------------------------------------------------

INSERT INTO cities (slug, name, latitude, longitude) VALUES
  ('paris', 'Paris', 48.8566, 2.3522),
  ('bordeaux', 'Bordeaux', 44.8378, -0.5792),
  ('toulouse', 'Toulouse', 43.6047, 1.4442),
  ('lyon', 'Lyon', 45.7640, 4.8357),
  ('marseille', 'Marseille', 43.2965, 5.3698),
  ('nantes', 'Nantes', 47.2184, -1.5536),
  ('lille', 'Lille', 50.6292, 3.0573),
  ('limoges', 'Limoges', 45.8336, 1.2611),
  ('besancon', 'Besançon', 47.2380, 6.0243),
  ('brest', 'Brest', 48.3905, -4.4861),
  ('nice', 'Nice', 43.7102, 7.2620),
  ('strasbourg', 'Strasbourg', 48.5734, 7.7521),
  ('clermont-ferrand', 'Clermont-Ferrand', 45.7772, 3.0870)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO providers (code, name) VALUES
  ('open_meteo', 'Open-Meteo'),
  ('meteo_france', 'Météo-France Open Data'),
  ('openweathermap', 'OpenWeatherMap'),
  ('weatherapi', 'WeatherAPI'),
  ('tomorrow_io', 'Tomorrow.io'),
  ('visual_crossing', 'Visual Crossing'),
  ('meteostat', 'Meteostat'),
  ('foreca', 'Foreca')
ON CONFLICT (code) DO NOTHING;
