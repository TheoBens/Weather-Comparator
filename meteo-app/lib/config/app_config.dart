import 'package:meteo_app/config/secrets.local.dart';

/// Config Supabase : secrets locaux (gitignored) avec repli `--dart-define`.
class AppConfig {
  static String get supabaseUrl {
    const fromEnv = String.fromEnvironment('SUPABASE_URL');
    if (fromEnv.isNotEmpty) return fromEnv;
    return LocalSecrets.supabaseUrl;
  }

  static String get supabaseAnonKey {
    const fromEnv = String.fromEnvironment('SUPABASE_ANON_KEY');
    if (fromEnv.isNotEmpty) return fromEnv;
    return LocalSecrets.supabaseAnonKey;
  }

  static bool get isConfigured =>
      supabaseUrl.isNotEmpty &&
      supabaseAnonKey.isNotEmpty &&
      !supabaseUrl.contains('VOTRE_REF');
}
