import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/dio_client.dart';
import '../models/skill_models.dart';

class SkillsRepository {
  final Dio _dio;
  const SkillsRepository(this._dio);

  Future<List<SkillModule>> fetchModules() async {
    final res = await _dio.get('/api/v1/skills/modules/');
    final list =
        (res.data['data']?['results'] ?? res.data['data'] ?? []) as List;
    return list
        .map((e) => SkillModule.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<SkillVideo>> fetchVideos(String moduleId) async {
    final res =
        await _dio.get('/api/v1/skills/modules/$moduleId/videos/');
    final list =
        (res.data['data']?['results'] ?? res.data['data'] ?? []) as List;
    return list
        .map((e) => SkillVideo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> markWatched(String videoId) async {
    await _dio.post('/api/v1/skills/videos/$videoId/watch/');
  }
}

final skillsRepositoryProvider = Provider<SkillsRepository>(
  (ref) => SkillsRepository(ref.watch(dioClientProvider)),
);
