import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/match.dart';
import '../data/match_repository.dart';

final matchRepositoryProvider = Provider((ref) => MatchRepository());

final groupMatchesProvider =
    FutureProvider.family<List<Match>, int>((ref, groupId) async {
  final repo = ref.watch(matchRepositoryProvider);
  return repo.getGroupMatches(groupId);
});
