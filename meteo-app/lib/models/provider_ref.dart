class ProviderRef {
  const ProviderRef({required this.code, required this.name});

  final String code;
  final String name;

  factory ProviderRef.fromJson(Map<String, dynamic> json) {
    final p = json['providers'];
    if (p is Map<String, dynamic>) {
      return ProviderRef(
        code: p['code'] as String? ?? '',
        name: p['name'] as String? ?? '',
      );
    }
    return ProviderRef(
      code: json['code'] as String? ?? '',
      name: json['name'] as String? ?? '',
    );
  }

  bool get supportsOpenMeteoHourly =>
      code == 'open_meteo' || code == 'meteo_france';
}
