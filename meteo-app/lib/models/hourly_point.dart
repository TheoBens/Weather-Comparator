class HourlyPoint {
  const HourlyPoint({
    required this.time,
    required this.temperatureC,
    required this.precipMm,
    required this.precipProbPct,
  });

  final DateTime time;
  final double? temperatureC;
  final double precipMm;
  final double? precipProbPct;
}
