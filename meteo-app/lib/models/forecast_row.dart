class ForecastRow {
  const ForecastRow({
    required this.providerCode,
    required this.providerName,
    required this.leadDays,
    required this.tempMin,
    required this.tempMax,
    required this.tempMean,
    required this.windSpeed,
    required this.precipProb,
    required this.precipMm,
    required this.issuedAt,
  });

  final String providerCode;
  final String providerName;
  final int leadDays;
  final double? tempMin;
  final double? tempMax;
  final double? tempMean;
  final double? windSpeed;
  final double? precipProb;
  final double? precipMm;
  final DateTime issuedAt;

  factory ForecastRow.fromJson(Map<String, dynamic> json) {
    final p = json['providers'] as Map<String, dynamic>?;
    double? asDouble(dynamic v) => v == null ? null : (v as num).toDouble();

    var prob = asDouble(json['precip_prob']);
    if (prob != null && prob <= 1) prob *= 100;

    return ForecastRow(
      providerCode: p?['code'] as String? ?? '',
      providerName: p?['name'] as String? ?? '',
      leadDays: json['lead_days'] as int,
      tempMin: asDouble(json['temp_min_c']),
      tempMax: asDouble(json['temp_max_c']),
      tempMean: asDouble(json['temp_mean_c']),
      windSpeed: asDouble(json['wind_speed_ms']),
      precipProb: prob,
      precipMm: asDouble(json['precip_amount_mm']),
      issuedAt: DateTime.parse(json['issued_at'] as String),
    );
  }
}
