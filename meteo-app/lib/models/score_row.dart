import 'package:meteo_app/models/metric_kind.dart';
import 'package:meteo_app/models/provider_ref.dart';

class ScoreRow {
  const ScoreRow({
    required this.cityId,
    required this.horizonDays,
    required this.provider,
    required this.maeTemp,
    required this.rainAccuracy,
    required this.maeWind,
    required this.nSamples,
  });

  final int cityId;
  final int horizonDays;
  final ProviderRef provider;
  final double? maeTemp;
  final double? rainAccuracy;
  final double? maeWind;
  final int nSamples;

  factory ScoreRow.fromJson(Map<String, dynamic> json) {
    double? d(dynamic v) => v == null ? null : (v as num).toDouble();
    return ScoreRow(
      cityId: json['city_id'] as int,
      horizonDays: json['horizon_days'] as int,
      provider: ProviderRef.fromJson(json),
      maeTemp: d(json['mae_temp_c']),
      rainAccuracy: d(json['rain_binary_accuracy']),
      maeWind: d(json['mae_wind_ms']),
      nSamples: json['n_samples'] as int? ?? 0,
    );
  }

  double? metricValue(MetricKind kind) {
    switch (kind) {
      case MetricKind.temperature:
        return maeTemp;
      case MetricKind.rainRisk:
        return rainAccuracy;
      case MetricKind.wind:
        return maeWind;
    }
  }
}
