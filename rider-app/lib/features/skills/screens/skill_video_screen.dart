import 'package:chewie/chewie.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../data/skills_repository.dart';
import '../models/skill_models.dart';
import '../providers/skills_provider.dart';

class SkillVideoScreen extends ConsumerWidget {
  final SkillModule module;
  const SkillVideoScreen({super.key, required this.module});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final videosAsync = ref.watch(skillVideosProvider(module.id));

    return Scaffold(
      appBar: AppBar(title: Text(module.title)),
      body: videosAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (videos) => videos.isEmpty
            ? const Center(child: Text('No videos in this module'))
            : ListView.builder(
                itemCount: videos.length,
                itemBuilder: (_, i) => _VideoTile(video: videos[i]),
              ),
      ),
    );
  }
}

class _VideoTile extends ConsumerStatefulWidget {
  final SkillVideo video;
  const _VideoTile({required this.video});

  @override
  ConsumerState<_VideoTile> createState() => _VideoTileState();
}

class _VideoTileState extends ConsumerState<_VideoTile> {
  VideoPlayerController? _vpCtrl;
  ChewieController? _chewieCtrl;
  bool _expanded = false;

  Future<void> _play() async {
    setState(() => _expanded = true);
    _vpCtrl = VideoPlayerController.networkUrl(Uri.parse(widget.video.videoUrl));
    await _vpCtrl!.initialize();
    _chewieCtrl = ChewieController(
      videoPlayerController: _vpCtrl!,
      autoPlay: true,
    );
    _vpCtrl!.addListener(_onVideoEnd);
    setState(() {});
  }

  void _onVideoEnd() {
    if (_vpCtrl!.value.position >= _vpCtrl!.value.duration &&
        _vpCtrl!.value.duration > Duration.zero) {
      ref.read(skillsRepositoryProvider).markWatched(widget.video.id);
      _vpCtrl!.removeListener(_onVideoEnd);
    }
  }

  @override
  void dispose() {
    _vpCtrl?.removeListener(_onVideoEnd);
    _chewieCtrl?.dispose();
    _vpCtrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ListTile(
          leading: const Icon(Icons.play_circle_outline),
          title: Text(widget.video.title),
          trailing: Text(
            '${(widget.video.durationSeconds ~/ 60)}m',
            style: const TextStyle(color: Colors.grey),
          ),
          onTap: _expanded ? null : _play,
        ),
        if (_expanded && _chewieCtrl != null)
          AspectRatio(
            aspectRatio: 16 / 9,
            child: Chewie(controller: _chewieCtrl!),
          ),
      ],
    );
  }
}
