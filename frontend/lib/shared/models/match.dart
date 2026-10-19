class Participant {
  final int userId;
  final String username;
  final String? displayName;
  final String? avatarUrl;
  final int? placement;
  final int? eloDelta;

  Participant({
    required this.userId,
    required this.username,
    this.displayName,
    this.avatarUrl,
    this.placement,
    this.eloDelta,
  });

  factory Participant.fromJson(Map<String, dynamic> json) {
    return Participant(
      userId: json['user_id'] as int,
      username: json['username'] as String,
      displayName: json['display_name'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      placement: json['placement'] as int?,
      eloDelta: json['elo_delta'] as int?,
    );
  }
}

class Confirmation {
  final int userId;
  final String username;
  final String? displayName;
  final String? avatarUrl;
  final bool? confirmed; // null = pendiente
  final DateTime? respondedAt;

  Confirmation({
    required this.userId,
    required this.username,
    this.displayName,
    this.avatarUrl,
    this.confirmed,
    this.respondedAt,
  });

  bool get isPending => confirmed == null;
  bool get isApproved => confirmed == true;
  bool get isRejected => confirmed == false;

  factory Confirmation.fromJson(Map<String, dynamic> json) {
    return Confirmation(
      userId: json['user_id'] as int,
      username: json['username'] as String,
      displayName: json['display_name'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      confirmed: json['confirmed'] as bool?,
      respondedAt: json['responded_at'] != null
          ? DateTime.parse(json['responded_at'] as String)
          : null,
    );
  }
}


class Match {
  final int id;
  final int groupId;
  final int gameId;
  final String? gameName;
  final int seasonId;
  final int registeredById;
  final int winnerId;
  final String status; // PENDING | CONFIRMED | REJECTED | CANCELLED
  final DateTime playedAt;
  final int? durationMinutes;
  final String? notes;
  final DateTime createdAt;
  final DateTime? verifiedAt;
  final List<Participant> participants;
  final List<Confirmation> confirmations;

  Match({
    required this.id,
    required this.groupId,
    required this.gameId,
    this.gameName,
    required this.seasonId,
    required this.registeredById,
    required this.winnerId,
    required this.status,
    required this.playedAt,
    this.durationMinutes,
    this.notes,
    required this.createdAt,
    this.verifiedAt,
    required this.participants,
    required this.confirmations,
  });

  bool get isPending => status == 'PENDING';
  bool get isConfirmed => status == 'CONFIRMED';
  bool get isRejected => status == 'REJECTED';
  bool get isCancelled => status == 'CANCELLED';

  factory Match.fromJson(Map<String, dynamic> json) {
    return Match(
      id: json['id'] as int,
      groupId: json['group_id'] as int,
      gameId: json['game_id'] as int,
      gameName: json['game_name'] as String?,
      seasonId: json['season_id'] as int,
      registeredById: json['registered_by_id'] as int,
      winnerId: json['winner_id'] as int,
      status: json['status'] as String,
      playedAt: DateTime.parse(json['played_at'] as String),
      durationMinutes: json['duration_minutes'] as int?,
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      verifiedAt: json['verified_at'] != null
          ? DateTime.parse(json['verified_at'] as String)
          : null,
      participants: (json['participants'] as List<dynamic>?)
              ?.map((p) => Participant.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [],
      confirmations: (json['confirmations'] as List<dynamic>?)
              ?.map((c) => Confirmation.fromJson(c as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class MatchCreate {
  final int gameId;
  final int winnerId;
  final List<int> participantIds;
  final DateTime? playedAt;
  final int? durationMinutes;
  final String? notes;

  MatchCreate({
    required this.gameId,
    required this.winnerId,
    required this.participantIds,
    this.playedAt,
    this.durationMinutes,
    this.notes,
  });

  Map<String, dynamic> toJson() => {
        'game_id': gameId,
        'winner_id': winnerId,
        'participant_ids': participantIds,
        if (playedAt != null) 'played_at': playedAt!.toIso8601String(),
        if (durationMinutes != null) 'duration_minutes': durationMinutes,
        if (notes != null && notes!.isNotEmpty) 'notes': notes,
      };
}
