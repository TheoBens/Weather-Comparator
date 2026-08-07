import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:meteo_app/models/hourly_point.dart';

class HourlyWeatherChart extends StatelessWidget {
  const HourlyWeatherChart({super.key, required this.hourly});

  final List<HourlyPoint> hourly;

  @override
  Widget build(BuildContext context) {
    if (hourly.isEmpty) {
      return const SizedBox(
        height: 200,
        child: Center(child: Text('Pas de données horaires')),
      );
    }

    final temps = hourly.map((e) => e.temperatureC).whereType<double>().toList();
    final minT = temps.isEmpty ? 0.0 : temps.reduce((a, b) => a < b ? a : b) - 2;
    final maxT = temps.isEmpty ? 20.0 : temps.reduce((a, b) => a > b ? a : b) + 2;

    return SizedBox(
      height: 220,
      child: Padding(
        padding: const EdgeInsets.only(right: 8, top: 8),
        child: LineChart(
          LineChartData(
            gridData: FlGridData(
              show: true,
              drawVerticalLine: false,
              horizontalInterval: 2,
              getDrawingHorizontalLine: (v) => FlLine(
                color: Colors.white.withValues(alpha: 0.08),
                strokeWidth: 1,
              ),
            ),
            titlesData: FlTitlesData(
              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 36,
                  getTitlesWidget: (v, _) => Text(
                    '${v.toInt()}°',
                    style: TextStyle(fontSize: 10, color: Colors.white.withValues(alpha: 0.5)),
                  ),
                ),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  interval: 3,
                  getTitlesWidget: (v, meta) {
                    final i = v.toInt();
                    if (i < 0 || i >= hourly.length) return const SizedBox.shrink();
                    if (hourly[i].time.hour % 3 != 0) return const SizedBox.shrink();
                    return Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        '${hourly[i].time.hour}h',
                        style: TextStyle(fontSize: 10, color: Colors.white.withValues(alpha: 0.5)),
                      ),
                    );
                  },
                ),
              ),
            ),
            borderData: FlBorderData(show: false),
            minY: minT,
            maxY: maxT,
            lineBarsData: [
              LineChartBarData(
                spots: [
                  for (var i = 0; i < hourly.length; i++)
                    if (hourly[i].temperatureC != null)
                      FlSpot(i.toDouble(), hourly[i].temperatureC!),
                ],
                isCurved: true,
                color: const Color(0xFF7DD3FC),
                barWidth: 2.5,
                dotData: const FlDotData(show: false),
                belowBarData: BarAreaData(
                  show: true,
                  color: const Color(0xFF7DD3FC).withValues(alpha: 0.12),
                ),
              ),
            ],
            lineTouchData: LineTouchData(
              touchTooltipData: LineTouchTooltipData(
                getTooltipItems: (touched) => touched.map((t) {
                  final i = t.x.toInt();
                  if (i < 0 || i >= hourly.length) return null;
                  final p = hourly[i];
                  return LineTooltipItem(
                    '${p.time.hour}h\n${p.temperatureC?.toStringAsFixed(1) ?? '—'}°\n${p.precipMm.toStringAsFixed(1)} mm',
                    const TextStyle(color: Colors.white, fontSize: 12),
                  );
                }).toList(),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Barres de pluie sous le graphique température.
class HourlyRainStrip extends StatelessWidget {
  const HourlyRainStrip({super.key, required this.hourly});

  final List<HourlyPoint> hourly;

  @override
  Widget build(BuildContext context) {
    if (hourly.isEmpty) return const SizedBox.shrink();
    final max = hourly.map((e) => e.precipMm).fold(0.0, (a, b) => a > b ? a : b);
    final scale = max < 0.05 ? 1.0 : max;

    return SizedBox(
      height: 48,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          for (final p in hourly)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 0.5),
                child: Container(
                  height: 40 * (p.precipMm / scale).clamp(0.0, 1.0),
                  decoration: BoxDecoration(
                    color: const Color(0xFF60A5FA).withValues(
                      alpha: 0.35 + 0.45 * (p.precipProbPct ?? 0) / 100,
                    ),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
