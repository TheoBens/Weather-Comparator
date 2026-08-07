import 'package:meteo_app/models/hourly_point.dart';
import 'package:meteo_app/models/provider_ref.dart';

class MetricAttribution {
  const MetricAttribution({required this.metricLabel, this.provider});

  final String metricLabel;
  final ProviderRef? provider;
}

class DayBundle {
  const DayBundle({
    required this.dayLabel,
    required this.dayOffset,
    required this.horizonDays,
    this.currentTemp,
    this.feelsLike,
    this.tempMin,
    this.tempMax,
    this.rainRiskPct,
    this.windMs,
    required this.hourly,
    required this.attributions,
    this.unavailableMessage,
    this.hourlyIsSynthetic = false,
  });

  final String dayLabel;
  /// 0 = aujourd'hui, 1..7 = J+1..J+7
  final int dayOffset;
  final int horizonDays;
  final double? currentTemp;
  final double? feelsLike;
  final double? tempMin;
  final double? tempMax;
  final double? rainRiskPct;
  final double? windMs;
  final List<HourlyPoint> hourly;
  final List<MetricAttribution> attributions;
  final String? unavailableMessage;
  final bool hourlyIsSynthetic;

  bool get hasData =>
      unavailableMessage == null &&
      (hourly.isNotEmpty || tempMin != null || currentTemp != null);
}
