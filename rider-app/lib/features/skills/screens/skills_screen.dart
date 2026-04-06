import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/skill_models.dart';
import '../providers/skills_provider.dart';
import 'skill_video_screen.dart';

class SkillsScreen extends ConsumerWidget {
  const SkillsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final modulesAsync = ref.watch(skillModulesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Skills')),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(skillModulesProvider),
        child: modulesAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Error: $e')),
          data: (modules) => modules.isEmpty
              ? const Center(child: Text('No modules available'))
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: modules.length,
                  itemBuilder: (_, i) => _ModuleCard(module: modules[i]),
                ),
        ),
      ),
    );
  }
}

class _ModuleCard extends StatelessWidget {
  final SkillModule module;
  const _ModuleCard({required this.module});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: const CircleAvatar(child: Icon(Icons.play_lesson)),
        title: Text(module.title,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(module.description, maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: Text('${module.totalVideos} videos',
            style: const TextStyle(color: Colors.grey, fontSize: 12)),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => SkillVideoScreen(module: module),
          ),
        ),
      ),
    );
  }
}
