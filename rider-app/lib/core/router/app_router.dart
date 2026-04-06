import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/otp_screen.dart';
import '../../features/home/screens/home_screen.dart';
import '../storage/token_storage.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final storage = ref.read(tokenStorageProvider);
  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) async {
      final token = await storage.getAccessToken();
      final isOnAuth =
          state.matchedLocation == '/login' || state.matchedLocation == '/otp';
      if (token != null && isOnAuth) return '/home';
      if (token == null && !isOnAuth) return '/login';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/otp',
        builder: (_, state) =>
            OtpScreen(phone: state.extra as String? ?? ''),
      ),
      GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
    ],
  );
});
