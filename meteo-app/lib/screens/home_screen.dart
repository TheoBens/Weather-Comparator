import 'package:flutter/material.dart';
import 'package:meteo_app/models/city.dart';
import 'package:meteo_app/models/day_bundle.dart';
import 'package:meteo_app/models/score_row.dart';
import 'package:meteo_app/services/open_meteo_service.dart';
import 'package:meteo_app/services/supabase_repository.dart';
import 'package:meteo_app/services/weather_orchestrator.dart';
import 'package:meteo_app/theme/app_theme.dart';
import 'package:meteo_app/widgets/hourly_chart.dart';
import 'package:meteo_app/widgets/source_attribution_bar.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final SupabaseRepository _repo;
  late final WeatherOrchestrator _orchestrator;

  List<City> _cities = [];
  City? _selectedCity;
  int _dayOffset = 0;

  List<ScoreRow> _scores = [];
  DayBundle? _bundle;

  bool _bootLoading = true;
  bool _dayLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _repo = SupabaseRepository(Supabase.instance.client);
    _orchestrator = WeatherOrchestrator(OpenMeteoService());
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    setState(() {
      _bootLoading = true;
      _error = null;
    });
    try {
      final cities = await _repo.fetchCities();
      final window = await _repo.fetchLatestScoreWindow();
      final scores = window != null ? await _repo.fetchScores(window) : <ScoreRow>[];

      if (!mounted) return;
      setState(() {
        _cities = cities;
        _selectedCity = cities.isNotEmpty ? cities.first : null;
        _scores = scores;
        _bootLoading = false;
      });
      if (_selectedCity != null) {
        await _loadDay();
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _bootLoading = false;
        _error = 'Impossible de charger les données : $e';
      });
    }
  }

  Future<void> _loadDay() async {
    final city = _selectedCity;
    if (city == null) return;

    setState(() {
      _dayLoading = true;
      _error = null;
    });

    try {
      final forecasts = await _repo.fetchLatestForecasts(city.id);
      final cityHasScores = _scores.any((s) => s.cityId == city.id);
      final bundle = await _orchestrator.loadDay(
        city: city,
        dayOffset: _dayOffset,
        scores: _scores,
        forecasts: forecasts,
        scoresAvailable: cityHasScores,
      );
      if (!mounted) return;
      setState(() {
        _bundle = bundle;
        _dayLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _dayLoading = false;
        _error = 'Erreur météo : $e';
      });
    }
  }

  Future<void> _onCityChanged(City? city) async {
    if (city == null) return;
    setState(() => _selectedCity = city);
    await _loadDay();
  }

  Future<void> _onDayChanged(int offset) async {
    if (offset == _dayOffset) return;
    setState(() => _dayOffset = offset);
    await _loadDay();
  }

  @override
  Widget build(BuildContext context) {
    if (_bootLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator(color: AppColors.accent)),
      );
    }

    if (_cities.isEmpty) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              _error ?? 'Aucune ville disponible dans le benchmark.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70),
            ),
          ),
        ),
      );
    }

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.accent,
          onRefresh: _bootstrap,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverToBoxAdapter(child: _buildHeader()),
              SliverToBoxAdapter(child: _buildDaySelector()),
              if (_dayLoading)
                const SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: CircularProgressIndicator(color: AppColors.accent),
                  ),
                )
              else if (_error != null)
                SliverToBoxAdapter(child: _buildErrorBanner(_error!))
              else if (_bundle != null)
                SliverToBoxAdapter(child: _buildContent(_bundle!)),
              const SliverToBoxAdapter(child: SizedBox(height: 24)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final city = _selectedCity!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
          const Icon(Icons.wb_sunny_outlined, color: AppColors.accent, size: 28),
          const SizedBox(width: 10),
          Expanded(
            child: DropdownButtonHideUnderline(
              child: DropdownButton<City>(
                value: city,
                isExpanded: true,
                dropdownColor: AppColors.surface,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
                items: [
                  for (final c in _cities)
                    DropdownMenuItem(
                      value: c,
                      child: Text('${c.name} (${c.country})'),
                    ),
                ],
                onChanged: _onCityChanged,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDaySelector() {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          for (var d = 0; d <= 7; d++)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: ChoiceChip(
                label: Text(d == 0 ? 'Aujourd\'hui' : 'J+$d'),
                selected: _dayOffset == d,
                onSelected: (_) => _onDayChanged(d),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildErrorBanner(String message) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.red.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(message, style: const TextStyle(color: Colors.white70)),
      ),
    );
  }

  Widget _buildContent(DayBundle bundle) {
    if (bundle.unavailableMessage != null) {
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(Icons.cloud_off, size: 48, color: Colors.white.withValues(alpha: 0.35)),
            const SizedBox(height: 16),
            Text(
              bundle.unavailableMessage!,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 15),
            ),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSummary(bundle),
          const SizedBox(height: 20),
          SourceAttributionBar(bundle: bundle),
          const SizedBox(height: 20),
          Text(
            'Prévisions horaires',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Colors.white.withValues(alpha: 0.85),
            ),
          ),
          const SizedBox(height: 8),
          HourlyWeatherChart(hourly: bundle.hourly),
          const SizedBox(height: 8),
          HourlyRainStrip(hourly: bundle.hourly),
          if (bundle.hourlyIsSynthetic)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Courbe estimée (pas de détail horaire pour cette source).',
                style: TextStyle(fontSize: 11, color: Colors.white.withValues(alpha: 0.45)),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSummary(DayBundle bundle) {
    final isToday = bundle.dayOffset == 0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            bundle.dayLabel,
            style: TextStyle(
              fontSize: 13,
              color: Colors.white.withValues(alpha: 0.55),
              letterSpacing: 0.5,
            ),
          ),
          if (isToday && bundle.currentTemp != null) ...[
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${bundle.currentTemp!.round()}°',
                  style: const TextStyle(
                    fontSize: 56,
                    fontWeight: FontWeight.w300,
                    height: 1,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 8),
                if (bundle.feelsLike != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text(
                      'Ressenti ${bundle.feelsLike!.round()}°',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.white.withValues(alpha: 0.6),
                      ),
                    ),
                  ),
              ],
            ),
          ] else if (bundle.tempMin != null || bundle.tempMax != null) ...[
            const SizedBox(height: 8),
            Text(
              _formatMinMax(bundle.tempMin, bundle.tempMax),
              style: const TextStyle(
                fontSize: 36,
                fontWeight: FontWeight.w300,
                color: Colors.white,
              ),
            ),
          ],
          const SizedBox(height: 16),
          Wrap(
            spacing: 16,
            runSpacing: 8,
            children: [
              _statChip(
                Icons.thermostat_outlined,
                'Min / max',
                _formatMinMax(bundle.tempMin, bundle.tempMax),
              ),
              _statChip(
                Icons.water_drop_outlined,
                'Risque pluie',
                bundle.rainRiskPct != null
                    ? '${bundle.rainRiskPct!.round()} %'
                    : '—',
              ),
              if (bundle.windMs != null)
                _statChip(
                  Icons.air,
                  'Vent',
                  '${bundle.windMs!.toStringAsFixed(1)} m/s',
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statChip(IconData icon, String label, String value) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: AppColors.accent.withValues(alpha: 0.8)),
        const SizedBox(width: 6),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(fontSize: 11, color: Colors.white.withValues(alpha: 0.45)),
            ),
            Text(value, style: const TextStyle(fontSize: 14, color: Colors.white)),
          ],
        ),
      ],
    );
  }

  String _formatMinMax(double? min, double? max) {
    if (min != null && max != null) return '${min.round()}° / ${max.round()}°';
    if (min != null) return '${min.round()}°';
    if (max != null) return '${max.round()}°';
    return '—';
  }
}
