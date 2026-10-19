class Group {
  final int id;
  final String name;
  final String? description;
  final String inviteCode;
  final int ownerId;
  final DateTime createdAt;
  final String? myRole;
  final int memberCount;
  final int gameCount;

  Group({
    required this.id,
    required this.name,
    this.description,
    required this.inviteCode,
    required this.ownerId,
    required this.createdAt,
    this.myRole,
    this.memberCount = 0,
    this.gameCount = 0,
  });

  bool get isManager => myRole == 'MANAGER';

  factory Group.fromJson(Map<String, dynamic> json) {
    return Group(
      id: json['id'] as int,
      name: json['name'] as String,
      description: json['description'] as String?,
      inviteCode: json['invite_code'] as String,
      ownerId: json['owner_id'] as int,
      createdAt: DateTime.parse(json['created_at'] as String),
      myRole: json['my_role'] as String?,
      memberCount: json['member_count'] as int? ?? 0,
      gameCount: json['game_count'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        'invite_code': inviteCode,
        'owner_id': ownerId,
        'created_at': createdAt.toIso8601String(),
        'my_role': myRole,
        'member_count': memberCount,
        'game_count': gameCount,
      };
}

class Member {
  final int userId;
  final String username;
  final String? displayName;
  final String? avatarUrl;
  final String role; // MANAGER | MEMBER
  final DateTime joinedAt;

  Member({
    required this.userId,
    required this.username,
    this.displayName,
    this.avatarUrl,
    required this.role,
    required this.joinedAt,
  });

  bool get isManager => role == 'MANAGER';

  factory Member.fromJson(Map<String, dynamic> json) {
    return Member(
      userId: json['user_id'] as int,
      username: json['username'] as String,
      displayName: json['display_name'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      role: json['role'] as String,
      joinedAt: DateTime.parse(json['joined_at'] as String),
    );
  }
}


class Season {
  final int id;
  final int number;
  final String name;
  final DateTime startDate;
  final DateTime endDate;
  final bool isActive;

  Season({
    required this.id,
    required this.number,
    required this.name,
    required this.startDate,
    required this.endDate,
    required this.isActive,
  });

  factory Season.fromJson(Map<String, dynamic> json) {
    return Season(
      id: json['id'] as int,
      number: json['number'] as int,
      name: json['name'] as String,
      startDate: DateTime.parse(json['start_date'] as String),
      endDate: DateTime.parse(json['end_date'] as String),
      isActive: json['is_active'] as bool? ?? false,
    );
  }
}
