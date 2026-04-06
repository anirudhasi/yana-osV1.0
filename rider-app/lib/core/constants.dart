import 'package:flutter/foundation.dart';

class AppConstants {
  /// Override at runtime:
  ///   flutter run --dart-define=API_BASE_URL=http://192.168.x.x:8000
  ///
  /// Defaults:
  ///   Web  → http://localhost:8000   (same machine, no proxy needed)
  ///   Android emulator → http://10.0.2.2:8000  (special alias to host loopback)
  ///   iOS simulator    → http://localhost:8000
  static String get apiBaseUrl {
    const override = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (override.isNotEmpty) return override;
    if (kIsWeb) return 'http://localhost:8000';
    // Android emulator routes to host via 10.0.2.2
    return 'http://10.0.2.2:8000';
  }
}
