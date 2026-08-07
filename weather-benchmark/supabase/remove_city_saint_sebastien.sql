-- Retire Saint-Sébastien du panel (données + ville).
-- Idempotent : ne fait rien si la ville n'existe pas.

DO $$
DECLARE
  cid INT;
BEGIN
  SELECT id INTO cid FROM cities WHERE slug = 'saint-sebastien';
  IF cid IS NULL THEN
    RAISE NOTICE 'Ville saint-sebastien absente, rien à faire.';
    RETURN;
  END IF;

  DELETE FROM forecast_scores WHERE city_id = cid;
  DELETE FROM forecasts WHERE city_id = cid;
  DELETE FROM observations WHERE city_id = cid;
  DELETE FROM cities WHERE id = cid;

  RAISE NOTICE 'Saint-Sébastien (id=%) supprimée avec ses données.', cid;
END $$;
