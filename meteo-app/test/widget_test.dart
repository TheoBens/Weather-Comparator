import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:meteo_app/config/app_config.dart';
import 'package:meteo_app/theme/app_theme.dart';

void main() {
  test('config Supabase présente', () {
    expect(AppConfig.isConfigured, isTrue);
    expect(AppConfig.supabaseUrl, contains('supabase.co'));
  });

  testWidgets('thème Material se construit', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildAppTheme(),
        home: const Scaffold(body: Text('Météo composite')),
      ),
    );
    expect(find.text('Météo composite'), findsOneWidget);
  });
}
