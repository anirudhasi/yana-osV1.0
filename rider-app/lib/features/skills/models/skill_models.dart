class SkillModule {
  final String id;
  final String title;
  final String description;
  final int totalVideos;

  const SkillModule({
    required this.id,
    required this.title,
    required this.description,
    required this.totalVideos,
  });

  factory SkillModule.fromJson(Map<String, dynamic> json) => SkillModule(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        description: json['description'] as String? ?? '',
        totalVideos: json['total_videos'] as int? ?? 0,
      );
}

class SkillVideo {
  final String id;
  final String title;
  final String videoUrl;
  final int durationSeconds;

  const SkillVideo({
    required this.id,
    required this.title,
    required this.videoUrl,
    required this.durationSeconds,
  });

  factory SkillVideo.fromJson(Map<String, dynamic> json) => SkillVideo(
        id: json['id'] as String? ?? '',
        title: json['title'] as String? ?? '',
        videoUrl: json['video_url'] as String? ?? '',
        durationSeconds: json['duration_seconds'] as int? ?? 0,
      );
}
