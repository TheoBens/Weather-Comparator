class City {
  const City({
    required this.id,
    required this.slug,
    required this.name,
    required this.country,
    required this.latitude,
    required this.longitude,
  });

  final int id;
  final String slug;
  final String name;
  final String country;
  final double latitude;
  final double longitude;

  factory City.fromJson(Map<String, dynamic> json) {
    return City(
      id: json['id'] as int,
      slug: json['slug'] as String,
      name: json['name'] as String,
      country: json['country'] as String? ?? 'FR',
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
    );
  }
}
