import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../constants.dart';
import '../storage/token_storage.dart';

final dioClientProvider = Provider<Dio>((ref) {
  final storage = ref.watch(tokenStorageProvider);
  final dio = Dio(BaseOptions(
    baseUrl: AppConstants.apiBaseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 15),
    headers: {'Content-Type': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final token = await storage.getAccessToken();
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      handler.next(options);
    },
    onError: (DioException err, handler) async {
      if (err.response?.statusCode == 401) {
        final refreshToken = await storage.getRefreshToken();
        if (refreshToken != null) {
          try {
            final res = await Dio().post(
              '${AppConstants.apiBaseUrl}/api/v1/auth/refresh',
              data: {'refresh_token': refreshToken},
            );
            final newAccess = res.data['data']['tokens']['access_token'] as String;
            final newRefresh = res.data['data']['tokens']['refresh_token'] as String;
            final riderId = await storage.getRiderId() ?? '';
            await storage.saveTokens(
              accessToken: newAccess,
              refreshToken: newRefresh,
              riderId: riderId,
            );
            err.requestOptions.headers['Authorization'] = 'Bearer $newAccess';
            final retryRes = await dio.fetch(err.requestOptions);
            handler.resolve(retryRes);
            return;
          } catch (_) {
            await storage.clear();
          }
        }
      }
      handler.next(err);
    },
  ));

  return dio;
});
