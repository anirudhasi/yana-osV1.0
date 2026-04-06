import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/skills_repository.dart';
import '../models/skill_models.dart';

final skillModulesProvider = FutureProvider<List<SkillModule>>((ref) {
  return ref.watch(skillsRepositoryProvider).fetchModules();
});

final skillVideosProvider =
    FutureProvider.family<List<SkillVideo>, String>((ref, moduleId) {
  return ref.watch(skillsRepositoryProvider).fetchVideos(moduleId);
});
