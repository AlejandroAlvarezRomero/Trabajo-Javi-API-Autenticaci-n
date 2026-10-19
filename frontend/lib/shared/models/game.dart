class Game {
  final int id;
  final int groupId;
  final int? bggId;
  final String name;
  final String? description;
  final String? imageUrl;
  final String? thumbnailUrl;
  final int? minPlayers;
  final int? maxPlayers;
  final int? avgPlaytimeMinutes;
  final int? yearPublished;
  final int? bggRanking;
  final double? bggRating;
  final DateTime createdAt;

  Game({
    required this.id,
    required this.groupId,
    this.bggId,
    required this.name,
    this.description,
    this.imageUrl,
    this.thumbnailUrl,
    this.minPlayers,
    this.maxPlayers,
    this.avgPlaytimeMinutes,
    this.yearPublished,
    this.bggRanking,
    this.bggRating,
    required this.createdAt,
  });

  String get playersSpan {
    if (minPlayers != null && maxPlayers != null) {
      return minPlayers == maxPlayers ? '$minPlayers jug.' : '$minPlayers-$maxPlayers jug.';
    }
    return '';
  }

  factory Game.fromJson(Map<String, dynamic> json) {
    return Game(
      id: json['id'] as int,
      groupId: json['group_id'] as int,
      bggId: json['bgg_id'] as int?,
      name: json['name'] as String,
      description: json['description'] as String?,
      imageUrl: json['image_url'] as String?,
      thumbnailUrl: json['thumbnail_url'] as String?,
      minPlayers: json['min_players'] as int?,
      maxPlayers: json['max_players'] as int?,
      avgPlaytimeMinutes: json['avg_playtime_minutes'] as int?,
      yearPublished: json['year_published'] as int?,
      bggRanking: json['bgg_ranking'] as int?,
      bggRating: (json['bgg_rating'] as num?)?.toDouble(),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class BggSearchResult {
  final int bggId;
  final String name;
  final int? yearPublished;

  BggSearchResult({
    required this.bggId,
    required this.name,
    this.yearPublished,
  });

  factory BggSearchResult.fromJson(Map<String, dynamic> json) {
    return BggSearchResult(
      bggId: json['bgg_id'] as int,
      name: json['name'] as String,
      yearPublished: json['year_published'] as int?,
    );
  }
}
