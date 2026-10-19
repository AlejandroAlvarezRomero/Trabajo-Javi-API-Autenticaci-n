import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/game.dart';
import '../data/game_repository.dart';

final gameRepositoryProvider = Provider((ref) => GameRepository());

final groupGamesProvider = FutureProvider.family<List<Game>, int>((ref, groupId) async {
  final repo = ref.watch(gameRepositoryProvider);
  return repo.getGroupGames(groupId);
});
