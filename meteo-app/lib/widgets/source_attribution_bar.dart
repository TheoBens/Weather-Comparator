import 'package:flutter/material.dart';
import 'package:meteo_app/models/day_bundle.dart';

class SourceAttributionBar extends StatelessWidget {
  const SourceAttributionBar({super.key, required this.bundle});

  final DayBundle bundle;

  @override
  Widget build(BuildContext context) {
    final parts = <String>[];
    for (final a in bundle.attributions) {
      final name = a.provider?.name;
      if (name == null) continue;
      parts.add('${a.metricLabel} · $name');
    }
    if (parts.isEmpty) return const SizedBox.shrink();

    return GestureDetector(
      onTap: () => _showDetail(context),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 14, color: Colors.white.withValues(alpha: 0.5)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                parts.join('  ·  '),
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.white.withValues(alpha: 0.55),
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showDetail(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF1A2744),
      showDragHandle: true,
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Sources (bench J+${bundle.horizonDays})',
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 12),
              ...bundle.attributions.map((a) {
                final p = a.provider;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    p == null
                        ? '${a.metricLabel} : pas encore de données'
                        : '${a.metricLabel} : ${p.name} (${p.code})',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.85)),
                  ),
                );
              }),
              if (bundle.hourlyIsSynthetic)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    'Courbe horaire estimée à partir des totaux journaliers '
                    'quand l’API ne fournit pas le détail heure par heure.',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.white.withValues(alpha: 0.5),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
