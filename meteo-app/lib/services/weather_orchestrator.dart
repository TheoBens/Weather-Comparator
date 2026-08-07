import 'package:meteo_app/models/city.dart';
import 'package:meteo_app/models/day_bundle.dart';
import 'package:meteo_app/models/forecast_row.dart';
import 'package:meteo_app/models/metric_kind.dart';
import 'package:meteo_app/models/hourly_point.dart';
import 'package:meteo_app/models/provider_ref.dart';
import 'package:meteo_app/models/score_row.dart';
import 'package:meteo_app/services/benchmark_resolver.dart';
import 'package:meteo_app/services/open_meteo_service.dart';

class WeatherOrchestrator {
  WeatherOrchestrator(this._openMeteo);

  final OpenMeteoService _openMeteo;

  Future<DayBundle> loadDay({
    required City city,
    required int dayOffset,
    required List<ScoreRow> scores,
    required List<ForecastRow> forecasts,
    required bool scoresAvailable,
  }) async {
    final now = DateTime.now();
    final dayLocal = DateTime(now.year, now.month, now.day).add(Duration(days: dayOffset));
    final horizonDays = dayOffset == 0 ? 1 : dayOffset;
    final dayLabel = _dayLabel(dayOffset);

    if (!scoresAvailable) {
      return DayBundle(
        dayLabel: dayLabel,
        dayOffset: dayOffset,
        horizonDays: horizonDays,
        hourly: const [],
        attributions: const [],
        unavailableMessage: 'Ville pas encore prise en compte dans le benchmark.',
      );
    }

    final winners = BenchmarkResolver.winnersForHorizon(
      scores: scores,
      cityId: city.id,
      horizonDays: horizonDays,
    );

    if (winners.values.every((p) => p == null)) {
      return DayBundle(
        dayLabel: dayLabel,
        dayOffset: dayOffset,
        horizonDays: horizonDays,
        hourly: const [],
        attributions: const [],
        unavailableMessage:
            'Pas encore assez de scores pour J+$horizonDays sur ${city.name}.',
      );
    }

    final tempProvider = winners[MetricKind.temperature];
    final rainProvider = winners[MetricKind.rainRisk];
    final windProvider = winners[MetricKind.wind];

    final tempRow = _forecastFor(forecasts, tempProvider, horizonDays);
    final rainRow = _forecastFor(forecasts, rainProvider, horizonDays);
    final windRow = _forecastFor(forecasts, windProvider, horizonDays);

    double? currentTemp;
    double? feelsLike;

    if (dayOffset == 0) {
      try {
        final model = tempProvider != null
            ? _openMeteo.modelForProvider(tempProvider.code)
            : null;
        final cur = await _openMeteo.fetchCurrent(
          city.latitude,
          city.longitude,
          model: model,
        );
        currentTemp = cur.temperatureC;
        feelsLike = cur.apparentTemperatureC;
      } catch (_) {
        /* garde null */
      }
    }

    final tempMin = tempRow?.tempMin;
    final tempMax = tempRow?.tempMax;
    final rainPct = rainRow?.precipProb;
    final windMs = windRow?.windSpeed;

    List<HourlyPoint> hourly = [];
    var synthetic = false;

    final hourlyTempProvider = tempProvider;
    final hourlyRainProvider = rainProvider;

    if (hourlyTempProvider != null &&
        hourlyTempProvider.supportsOpenMeteoHourly) {
      try {
        hourly = await _openMeteo.fetchHourlyForDate(
          lat: city.latitude,
          lon: city.longitude,
          dayLocal: dayLocal,
          model: _openMeteo.modelForProvider(hourlyTempProvider.code),
        );
      } catch (_) {
        hourly = [];
      }
    }

    if (hourly.isEmpty) {
      synthetic = true;
      hourly = _openMeteo.synthesizeHourlyFromDaily(
        dayLocal: dayLocal,
        tempMin: tempMin,
        tempMax: tempMax,
        precipMm: rainRow?.precipMm,
        precipProbPct: rainPct,
      );
    } else if (hourlyRainProvider != null &&
        hourlyRainProvider.code != hourlyTempProvider?.code &&
        !hourlyRainProvider.supportsOpenMeteoHourly) {
      // Mélange discret : probabilités / pluie de la source bench si dispo
      final prob = rainPct;
      final mmPerH = (rainRow?.precipMm ?? 0) / 24;
      hourly = hourly
          .map(
            (p) => HourlyPoint(
              time: p.time,
              temperatureC: p.temperatureC,
              precipMm: mmPerH,
              precipProbPct: prob ?? p.precipProbPct,
            ),
          )
          .toList();
    }

    double? displayMin = tempMin;
    double? displayMax = tempMax;
    double? displayRainPct = rainPct;

    if (dayOffset == 0 && hourly.isNotEmpty) {
      final temps = hourly.map((e) => e.temperatureC).whereType<double>();
      if (temps.isNotEmpty) {
        displayMin = temps.reduce((a, b) => a < b ? a : b);
        displayMax = temps.reduce((a, b) => a > b ? a : b);
      }
      final probs = hourly.map((e) => e.precipProbPct).whereType<double>();
      if (probs.isNotEmpty) {
        displayRainPct = probs.reduce((a, b) => a > b ? a : b);
      }
    }

    final attributions = [
      MetricAttribution(
        metricLabel: MetricKind.temperature.label,
        provider: tempProvider,
      ),
      MetricAttribution(
        metricLabel: MetricKind.rainRisk.label,
        provider: rainProvider,
      ),
      MetricAttribution(
        metricLabel: MetricKind.wind.label,
        provider: windProvider,
      ),
    ];

    return DayBundle(
      dayLabel: dayLabel,
      dayOffset: dayOffset,
      horizonDays: horizonDays,
      currentTemp: currentTemp,
      feelsLike: feelsLike,
      tempMin: displayMin,
      tempMax: displayMax,
      rainRiskPct: displayRainPct,
      windMs: windMs,
      hourly: hourly,
      attributions: attributions,
      hourlyIsSynthetic: synthetic,
    );
  }

  ForecastRow? _forecastFor(
    List<ForecastRow> forecasts,
    ProviderRef? provider,
    int leadDays,
  ) {
    if (provider == null) return null;
    for (final f in forecasts) {
      if (f.providerCode == provider.code && f.leadDays == leadDays) {
        return f;
      }
    }
    return null;
  }

  String _dayLabel(int offset) {
    if (offset == 0) return 'Aujourd\'hui';
    return 'J+$offset';
  }
}
