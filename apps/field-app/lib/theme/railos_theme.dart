import 'package:flutter/material.dart';
import 'railos_tokens.dart';

/// RailOS Cockpit Design System Theme for Flutter
/// Directly mapped to DESIGN.md and Next.js Control Center tokens.
class RailOSTheme {
  RailOSTheme._();

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: RailOSTokens.bg_canvas,
      cardColor: RailOSTokens.bg_panel,
      canvasColor: RailOSTokens.bg_canvas,
      dividerColor: RailOSTokens.border_default,
      primaryColor: RailOSTokens.accent,

      // Shared text rhythm for dense field screens. Individual widgets may
      // use a monospace face for identifiers, but reading copy stays at 16dp
      // or larger so text scaling remains useful on a moving worksite.
      textTheme: const TextTheme(
        displaySmall: TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 24,
          height: 1.2,
          fontWeight: FontWeight.w700,
        ),
        headlineSmall: TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 20,
          height: 1.25,
          fontWeight: FontWeight.w700,
        ),
        titleLarge: TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 18,
          height: 1.25,
          fontWeight: FontWeight.w700,
        ),
        titleMedium: TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 16,
          height: 1.3,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 16,
          height: 1.5,
        ),
        bodyMedium: TextStyle(
          color: RailOSTokens.text_secondary,
          fontSize: 14,
          height: 1.45,
        ),
        bodySmall: TextStyle(
          color: RailOSTokens.text_muted,
          fontSize: 12,
          height: 1.4,
        ),
        labelLarge: TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 14,
          fontWeight: FontWeight.w700,
        ),
        labelMedium: TextStyle(
          color: RailOSTokens.text_secondary,
          fontSize: 13,
          fontWeight: FontWeight.w600,
        ),
      ),

      colorScheme: const ColorScheme.dark(
        primary: RailOSTokens.accent,
        onPrimary: RailOSTokens.bg_canvas,
        secondary: RailOSTokens.status_info_fg,
        onSecondary: RailOSTokens.bg_canvas,
        surface: RailOSTokens.bg_surface,
        onSurface: RailOSTokens.text_primary,
        surfaceContainer: RailOSTokens.bg_panel,
        surfaceContainerHigh: RailOSTokens.bg_elevated,
        outline: RailOSTokens.border_default,
        outlineVariant: RailOSTokens.border_subtle,
        error: RailOSTokens.status_critical_fg,
        onError: RailOSTokens.bg_canvas,
      ),

      appBarTheme: const AppBarTheme(
        backgroundColor: RailOSTokens.bg_surface,
        foregroundColor: RailOSTokens.text_primary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: RailOSTokens.text_secondary),
        actionsIconTheme: IconThemeData(color: RailOSTokens.text_secondary),
        shape: Border(
          bottom: BorderSide(color: RailOSTokens.border_default, width: 1),
        ),
      ),

      cardTheme: CardThemeData(
        color: RailOSTokens.bg_panel,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
          side: const BorderSide(color: RailOSTokens.border_default, width: 1),
        ),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size.fromHeight(RailOSTokens.minTouchTargetDp),
          backgroundColor: RailOSTokens.accent,
          foregroundColor: RailOSTokens.bg_canvas,
          disabledBackgroundColor: RailOSTokens.bg_elevated,
          disabledForegroundColor: RailOSTokens.text_muted,
          elevation: 0,
          textStyle: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 14,
            letterSpacing: 0.2,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          ),
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(RailOSTokens.minTouchTargetDp),
          foregroundColor: RailOSTokens.text_primary,
          side: const BorderSide(color: RailOSTokens.border_default, width: 1),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: RailOSTokens.text_secondary,
          minimumSize: const Size(48, 48),
          textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: RailOSTokens.bg_surface,
        labelStyle: const TextStyle(
          color: RailOSTokens.text_secondary,
          fontSize: 13,
        ),
        hintStyle: const TextStyle(
          color: RailOSTokens.text_muted,
          fontSize: 13,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 14,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          borderSide: const BorderSide(
            color: RailOSTokens.border_default,
            width: 1,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          borderSide: const BorderSide(
            color: RailOSTokens.border_default,
            width: 1,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          borderSide: const BorderSide(color: RailOSTokens.accent, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          borderSide: const BorderSide(
            color: RailOSTokens.status_critical_border,
            width: 1,
          ),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          borderSide: const BorderSide(
            color: RailOSTokens.status_critical_fg,
            width: 1.5,
          ),
        ),
      ),

      chipTheme: ChipThemeData(
        backgroundColor: RailOSTokens.bg_panel,
        selectedColor: RailOSTokens.bg_elevated,
        side: const BorderSide(color: RailOSTokens.border_default, width: 1),
        labelStyle: const TextStyle(
          color: RailOSTokens.text_secondary,
          fontSize: 12,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
        ),
      ),

      dialogTheme: DialogThemeData(
        backgroundColor: RailOSTokens.bg_surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
          side: const BorderSide(color: RailOSTokens.border_default, width: 1),
        ),
        titleTextStyle: const TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 17,
          fontWeight: FontWeight.bold,
        ),
        contentTextStyle: const TextStyle(
          color: RailOSTokens.text_secondary,
          fontSize: 14,
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor: RailOSTokens.bg_elevated,
        contentTextStyle: const TextStyle(
          color: RailOSTokens.text_primary,
          fontSize: 13,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          side: const BorderSide(color: RailOSTokens.border_default, width: 1),
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
