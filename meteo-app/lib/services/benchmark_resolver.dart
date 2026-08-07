import 'package:meteo_app/models/metric_kind.dart';
import 'package:meteo_app/models/provider_ref.dart';
import 'package:meteo_app/models/score_row.dart';

typedef HorizonWinners = Map<MetricKind, ProviderRef?>;

class BenchmarkResolver {
  /// Meilleur fournisseur par métrique pour une ville et un horizon (J+n).
  static HorizonWinners winnersForHorizon({
    required List<ScoreRow> scores,
    required int cityId,
    required int horizonDays,
  }) {
    final rows = scores
        .where((s) => s.cityId == cityId && s.horizonDays == horizonDays)
        .toList();

    final result = <MetricKind, ProviderRef?>{};
    for (final kind in MetricKind.values) {
      result[kind] = _bestProvider(rows, kind);
    }
    return result;
  }

  static ProviderRef? _bestProvider(List<ScoreRow> rows, MetricKind kind) {
    final higher = kind.higherIsBetter;
    ScoreRow? best;
    for (final row in rows) {
      final v = row.metricValue(kind);
      if (v == null) continue;
      if (best == null) {
        best = row;
        continue;
      }
      final bv = best.metricValue(kind)!;
      final better = higher ? v > bv : v < bv;
      if (better ||
          (v == bv &&
              row.provider.code.compareTo(best.provider.code) < 0)) {
        best = row;
      }
    }
    return best?.provider;
  }
}
