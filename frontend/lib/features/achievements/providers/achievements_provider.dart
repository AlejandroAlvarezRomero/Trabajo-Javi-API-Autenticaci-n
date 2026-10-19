import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/achievement.dart';
import '../data/achievement_repository.dart';

final achievementRepositoryProvider = Provider((ref) => AchievementRepository());

final allAchievementsProvider = FutureProvider<List<Achievement>>((ref) async {
  return ref.watch(achievementRepositoryProvider).getAllAchievements();
});

final myAchievementsProvider =
    FutureProvider<List<UserAchievement>>((ref) async {
  return ref.watch(achievementRepositoryProvider).getMyAchievements();
});
