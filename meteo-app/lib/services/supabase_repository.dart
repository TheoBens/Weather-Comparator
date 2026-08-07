import 'package:meteo_app/models/city.dart';
import 'package:meteo_app/models/forecast_row.dart';
import 'package:meteo_app/models/score_row.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ScoreWindow {
  const ScoreWindow({required this.start, required this.end});

  final String start;
  final String end;
}

class SupabaseRepository {
  SupabaseRepository(this._client);

  final SupabaseClient _client;

  Future<List<City>> fetchCities() async {
    final data = await _client
        .from('cities')
        .select('id, slug, name, country, latitude, longitude')
        .order('name');
    return (data as List)
        .map((e) => City.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<ScoreWindow?> fetchLatestScoreWindow() async {
    final rows = await _client
        .from('forecast_scores')
        .select('score_window_start, score_window_end');
    if ((rows as List).isEmpty) return null;

    final startsByEnd = <String, List<String>>{};
    for (final raw in rows) {
      final m = Map<String, dynamic>.from(raw as Map);
      final start = (m['score_window_start'] as String).substring(0, 10);
      final end = (m['score_window_end'] as String).substring(0, 10);
      startsByEnd.putIfAbsent(end, () => []).add(start);
    }
    final sortedEnds = startsByEnd.keys.toList()..sort((a, b) => b.compareTo(a));
    final end = sortedEnds.first;
    final starts = startsByEnd[end]!..sort((a, b) => b.compareTo(a));
    return ScoreWindow(start: starts.first, end: end);
  }

  Future<List<ScoreRow>> fetchScores(ScoreWindow window) async {
    final data = await _client
        .from('forecast_scores')
        .select(
          'city_id, horizon_days, n_samples, mae_temp_c, rain_binary_accuracy, mae_wind_ms, providers(code, name)',
        )
        .eq('score_window_start', window.start)
        .eq('score_window_end', window.end);
    return (data as List)
        .map((e) => ScoreRow.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<List<ForecastRow>> fetchLatestForecasts(int cityId) async {
    final data = await _client
        .from('forecasts')
        .select(
          'lead_days, issued_at, temp_min_c, temp_max_c, temp_mean_c, wind_speed_ms, precip_prob, precip_amount_mm, providers(code, name)',
        )
        .eq('city_id', cityId)
        .order('issued_at', ascending: false)
        .limit(800);

    final latest = <String, ForecastRow>{};
    for (final raw in data as List) {
      final row = ForecastRow.fromJson(Map<String, dynamic>.from(raw as Map));
      final key = '${row.providerCode}:${row.leadDays}';
      latest.putIfAbsent(key, () => row);
    }
    return latest.values.toList();
  }
}
