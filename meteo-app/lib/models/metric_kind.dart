enum MetricKind {
  temperature,
  rainRisk,
  wind,
}

extension MetricKindX on MetricKind {
  String get label {
    switch (this) {
      case MetricKind.temperature:
        return 'Température';
      case MetricKind.rainRisk:
        return 'Pluie';
      case MetricKind.wind:
        return 'Vent';
    }
  }

  /// Champ dans forecast_scores (plus bas = mieux sauf rainRisk).
  String get scoreField {
    switch (this) {
      case MetricKind.temperature:
        return 'mae_temp_c';
      case MetricKind.rainRisk:
        return 'rain_binary_accuracy';
      case MetricKind.wind:
        return 'mae_wind_ms';
    }
  }

  bool get higherIsBetter => this == MetricKind.rainRisk;
}
