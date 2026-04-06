import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/dio_client.dart';
import '../models/auth_models.dart';

class AuthRepository {
  final Dio _dio;
  const AuthRepository(this._dio);

  Future<void> sendOtp(String phone) async {
    await _dio.post('/api/v1/auth/rider/send-otp', data: {'phone': phone});
  }

  Future<AuthResult> verifyOtp(String phone, String otp) async {
    final res = await _dio.post(
      '/api/v1/auth/rider/verify-otp',
      data: {'phone': phone, 'otp': otp},
    );
    return AuthResult.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> logout() async {
    await _dio.post('/api/v1/auth/logout');
  }
}

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(ref.watch(dioClientProvider)),
);
