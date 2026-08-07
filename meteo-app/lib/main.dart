import 'package:flutter/material.dart';
import 'package:meteo_app/config/app_config.dart';
import 'package:meteo_app/screens/home_screen.dart';
import 'package:meteo_app/theme/app_theme.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (AppConfig.isConfigured) {
    await Supabase.initialize(
      url: AppConfig.supabaseUrl,
      publishableKey: AppConfig.supabaseAnonKey,
    );
  }

  runApp(const MeteoApp());
}

class MeteoApp extends StatelessWidget {
  const MeteoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Météo composite',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: AppConfig.isConfigured
          ? const HomeScreen()
          : const _ConfigMissingScreen(),
    );
  }
}

class _ConfigMissingScreen extends StatelessWidget {
  const _ConfigMissingScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.settings, size: 40, color: AppColors.accent),
              const SizedBox(height: 16),
              const Text(
                'Configuration Supabase requise',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Colors.white),
              ),
              const SizedBox(height: 12),
              Text(
                'Générez les secrets locaux :\n\n'
                'python tool/sync_secrets.py\n\n'
                'Puis relancez l’app (ou .\\run_android.ps1).',
                style: TextStyle(
                  fontSize: 14,
                  height: 1.5,
                  color: Colors.white.withValues(alpha: 0.7),
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
