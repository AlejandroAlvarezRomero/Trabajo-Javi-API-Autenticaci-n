import 'group.dart';

class GroupStats {
  final int userId;
  final String username;
  final String? displayName;
  final String? avatarUrl;
  final int elo;
  final String rank; // HIERRO | BRONCE | PLATA | ORO | PLATINO | DIAMANTE
  final int wins;
  final int losses;
  final int gamesPlayed;
  final double winRate;
  final int totalPlayMinutes;

  GroupStats({
    required this.userId,
    required this.username,
    this.displayName,
    this.avatarUrl,
    required this.elo,
    required this.rank,
    required this.wins,
    required this.losses,
    required this.gamesPlayed,
    required this.winRate,
    required this.totalPlayMinutes,
  });

  factory GroupStats.fromJson(Map<String, dynamic> json) {
    return GroupStats(
      userId: json['user_id'] as int,
      username: json['username'] as String,
      displayName: json['display_name'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      elo: json['elo'] as int,
      rank: json['rank'] as String,
      wins: json['wins'] as int,
      losses: json['losses'] as int,
      gamesPlayed: json['games_played'] as int,
      winRate: (json['win_rate'] as num).toDouble(),
      totalPlayMinutes: json['total_play_minutes'] as int,
    );
  }
}


class Leaderboard {
  final Season season;
  final List<GroupStats> entries;

  Leaderboard({
    required this.season,
    required this.entries,
  });

  factory Leaderboard.fromJson(Map<String, dynamic> json) {
    return Leaderboard(
      season: Season.fromJson(json['season'] as Map<String, dynamic>),
      entries: (json['entries'] as List<dynamic>?)
              ?.map((e) => GroupStats.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
