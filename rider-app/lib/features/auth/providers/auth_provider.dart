import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/storage/token_storage.dart';
import '../data/auth_repository.dart';
import '../models/auth_models.dart';

// Stores the logged-in rider ID; null when unauthenticated.
final riderIdProvider = StateProvider<String?>((ref) => null);

class AuthNotifier extends AsyncNotifier<AuthUser?> {
  @override
  Future<AuthUser?> build() async {
    final storage = ref.watch(tokenStorageProvider);
    final riderId = await storage.getRiderId();
    if (riderId == null) return null;
    return AuthUser(id: riderId, phone: '', role: 'RIDER');
  }

  Future<void> sendOtp(String phone) async {
    final repo = ref.read(authRepositoryProvider);
    await repo.sendOtp(phone);
  }

  Future<AuthResult> verifyOtp(String phone, String otp) async {
    final repo = ref.read(authRepositoryProvider);
    final result = await repo.verifyOtp(phone, otp);
    final storage = ref.read(tokenStorageProvider);
    await storage.saveTokens(
      accessToken: result.tokens.accessToken,
      refreshToken: result.tokens.refreshToken,
      riderId: result.user.id,
    );
    ref.read(riderIdProvider.notifier).state = result.user.id;
    state = AsyncData(result.user);
    return result;
  }

  Future<void> logout() async {
    final repo = ref.read(authRepositoryProvider);
    final storage = ref.read(tokenStorageProvider);
    try {
      await repo.logout();
    } catch (_) {}
    await storage.clear();
    ref.read(riderIdProvider.notifier).state = null;
    state = const AsyncData(null);
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, AuthUser?>(
  AuthNotifier.new,
);
