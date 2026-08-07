import 'package:flutter/material.dart';

class AppColors {
  static const background = Color(0xFF0F1729);
  static const surface = Color(0xFF1A2744);
  static const accent = Color(0xFF7DD3FC);
  static const rain = Color(0xFF60A5FA);
}

ThemeData buildAppTheme() {
  const scheme = ColorScheme.dark(
    primary: AppColors.accent,
    surface: AppColors.surface,
    onSurface: Colors.white,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.background,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      elevation: 0,
      centerTitle: false,
    ),
    chipTheme: ChipThemeData(
      backgroundColor: Colors.white.withValues(alpha: 0.06),
      selectedColor: AppColors.accent.withValues(alpha: 0.25),
      labelStyle: const TextStyle(color: Colors.white70, fontSize: 13),
      secondaryLabelStyle: const TextStyle(color: Colors.white, fontSize: 13),
      side: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
  );
}
