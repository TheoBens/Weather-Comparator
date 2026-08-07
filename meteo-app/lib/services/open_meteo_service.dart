import 'dart:convert';
import 'dart:math' as math;

import 'package:http/http.dart' as http;
import 'package:meteo_app/models/hourly_point.dart';

class OpenMeteoCurrent {
  const OpenMeteoCurrent({
    required this.temperatureC,
    required this.apparentTemperatureC,
    required this.precipitationMm,
  });

  final double? temperatureC;
  final double? apparentTemperatureC;
  final double? precipitationMm;
}

class OpenMeteoService {
  static const _forecast = 'https://api.open-meteo.com/v1/forecast';

  Future<OpenMeteoCurrent> fetchCurrent(double lat, double lon, {String? model}) async {
    final uri = Uri.parse(_forecast).replace(
      queryParameters: {
        'latitude': '$lat',
        'longitude': '$lon',
        if (model != null) 'models': model,
        'current': 'temperature_2m,apparent_temperature,precipitation',
        'timezone': 'Europe/Paris',
      },
    );
    final res = await http.get(uri);
    if (res.statusCode != 200) {
      throw Exception('Open-Meteo current: ${res.statusCode}');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final cur = data['current'] as Map<String, dynamic>? ?? {};
    double? d(dynamic v) => v == null ? null : (v as num).toDouble();
    return OpenMeteoCurrent(
      temperatureC: d(cur['temperature_2m']),
      apparentTemperatureC: d(cur['apparent_temperature']),
      precipitationMm: d(cur['precipitation']),
    );
  }

  Future<List<HourlyPoint>> fetchHourlyForDate({
    required double lat,
    required double lon,
    required DateTime dayLocal,
    String? model,
  }) async {
    final uri = Uri.parse(_forecast).replace(
      queryParameters: {
        'latitude': '$lat',
        'longitude': '$lon',
        if (model != null) 'models': model,
        'hourly': 'temperature_2m,precipitation,precipitation_probability',
        'forecast_days': '8',
        'timezone': 'Europe/Paris',
      },
    );
    final res = await http.get(uri);
    if (res.statusCode != 200) {
      throw Exception('Open-Meteo hourly: ${res.statusCode}');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final hourly = data['hourly'] as Map<String, dynamic>? ?? {};
    final times = (hourly['time'] as List?)?.cast<String>() ?? [];
    final temps = hourly['temperature_2m'] as List?;
    final precs = hourly['precipitation'] as List?;
    final probs = hourly['precipitation_probability'] as List?;

    final target = DateTime(dayLocal.year, dayLocal.month, dayLocal.day);
    final out = <HourlyPoint>[];
    for (var i = 0; i < times.length; i++) {
      final t = DateTime.parse(times[i]);
      if (t.year != target.year || t.month != target.month || t.day != target.day) {
        continue;
      }
      double? temp = temps != null && i < temps.length ? (temps[i] as num?)?.toDouble() : null;
      final mm = precs != null && i < precs.length ? (precs[i] as num?)?.toDouble() ?? 0 : 0.0;
      double? prob = probs != null && i < probs.length ? (probs[i] as num?)?.toDouble() : null;
      out.add(HourlyPoint(time: t, temperatureC: temp, precipMm: mm, precipProbPct: prob));
    }
    return out;
  }

  /// Courbe horaire approximative à partir d'une prévision journalière (API payantes).
  List<HourlyPoint> synthesizeHourlyFromDaily({
    required DateTime dayLocal,
    required double? tempMin,
    required double? tempMax,
    required double? precipMm,
    required double? precipProbPct,
  }) {
    final minT = tempMin ?? tempMax ?? 12.0;
    final maxT = tempMax ?? tempMin ?? minT;
    final rain = precipMm ?? 0;
    final prob = precipProbPct;
    final points = <HourlyPoint>[];
    for (var h = 0; h < 24; h++) {
      final t = DateTime(dayLocal.year, dayLocal.month, dayLocal.day, h);
      // Sinusoïde simple : min vers 6h, max vers 15h
      final phase = (h - 6) / 24 * 2 * math.pi;
      final temp = minT + (maxT - minT) * (0.5 + 0.5 * math.sin(phase - math.pi / 2));
      final hourRain = rain / 24;
      points.add(
        HourlyPoint(
          time: t,
          temperatureC: temp,
          precipMm: hourRain,
          precipProbPct: prob,
        ),
      );
    }
    return points;
  }

  String? modelForProvider(String code) {
    if (code == 'meteo_france') return 'meteofrance_seamless';
    return null;
  }
}
