class Achievement {
  final int id;
  final String code;
  final String name;
  final String? description;
  final String? iconUrl;

  Achievement({
    required this.id,
    required this.code,
    required this.name,
    this.description,
    this.iconUrl,
  });

  factory Achievement.fromJson(Map<String, dynamic> json) {
    return Achievement(
      id: json['id'] as int,
      code: json['code'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      iconUrl: json['icon_url'] as String?,
    );
  }
}

class UserAchievement {
  final Achievement achievement;
  final int? groupId;
  final DateTime unlockedAt;

  UserAchievement({
    required this.achievement,
    this.groupId,
    required this.unlockedAt,
  });

  factory UserAchievement.fromJson(Map<String, dynamic> json) {
    return UserAchievement(
      achievement:
          Achievement.fromJson(json['achievement'] as Map<String, dynamic>),
      groupId: json['group_id'] as int?,
      unlockedAt: DateTime.parse(json['unlocked_at'] as String),
    );
  }
}
