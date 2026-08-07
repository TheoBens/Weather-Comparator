-- Lecture publique (clé anon) pour l'app mobile meteo-app
-- À exécuter dans le SQL Editor Supabase, ou : python weather-benchmark/scripts/apply_rls_anon.py

-- 1) Droits SQL (requis en plus des politiques RLS)
GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT ON TABLE cities TO anon, authenticated;
GRANT SELECT ON TABLE providers TO anon, authenticated;
GRANT SELECT ON TABLE forecasts TO anon, authenticated;
GRANT SELECT ON TABLE forecast_scores TO anon, authenticated;

-- 2) Politiques RLS
ALTER TABLE cities ENABLE ROW LEVEL SECURITY;
ALTER TABLE providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecast_scores ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cities_read_anon ON cities;
CREATE POLICY cities_read_anon ON cities
  FOR SELECT TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS providers_read_anon ON providers;
CREATE POLICY providers_read_anon ON providers
  FOR SELECT TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS forecasts_read_anon ON forecasts;
CREATE POLICY forecasts_read_anon ON forecasts
  FOR SELECT TO anon, authenticated
  USING (true);

DROP POLICY IF EXISTS forecast_scores_read_anon ON forecast_scores;
CREATE POLICY forecast_scores_read_anon ON forecast_scores
  FOR SELECT TO anon, authenticated
  USING (true);
