import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/group.dart';
import '../../../shared/models/stats.dart';
import '../data/stats_repository.dart';

final statsRepositoryProvider = Provider((ref) => StatsRepository());

final leaderboardProvider =
    FutureProvider.family<Leaderboard, int>((ref, groupId) async {
  final repo = ref.watch(statsRepositoryProvider);
  return repo.getLeaderboard(groupId);
});

final myStatsProvider =
    FutureProvider.family<GroupStats, int>((ref, groupId) async {
  final repo = ref.watch(statsRepositoryProvider);
  return repo.getMyStats(groupId);
});

final seasonsProvider =
    FutureProvider.family<List<Season>, int>((ref, groupId) async {
  final repo = ref.watch(statsRepositoryProvider);
  return repo.getGroupSeasons(groupId);
});
