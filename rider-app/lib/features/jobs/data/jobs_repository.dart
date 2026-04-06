import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/dio_client.dart';
import '../models/job_models.dart';

class JobsRepository {
  final Dio _dio;
  const JobsRepository(this._dio);

  Future<List<JobSlot>> fetchPublishedSlots() async {
    final res = await _dio.get(
      '/api/v1/marketplace/slots/',
      queryParameters: {'status': 'PUBLISHED'},
    );
    final list = (res.data['data']?['results'] ?? res.data['data'] ?? []) as List;
    return list.map((e) => JobSlot.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> applyToSlot(String slotId) async {
    await _dio.post('/api/v1/marketplace/slots/$slotId/apply/');
  }

  Future<List<JobSlot>> fetchMyApplications(String riderId) async {
    final res = await _dio
        .get('/api/v1/marketplace/riders/$riderId/applications/');
    final list = (res.data['data']?['results'] ?? res.data['data'] ?? []) as List;
    return list.map((e) => JobSlot.fromJson(e as Map<String, dynamic>)).toList();
  }
}

final jobsRepositoryProvider = Provider<JobsRepository>(
  (ref) => JobsRepository(ref.watch(dioClientProvider)),
);
