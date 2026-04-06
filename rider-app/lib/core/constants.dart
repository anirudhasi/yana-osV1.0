class AppConstants {
  // Android emulator uses 10.0.2.2 to reach the host machine.
  // Override at runtime: flutter run --dart-define=API_BASE_URL=http://<ip>:8000
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
}
