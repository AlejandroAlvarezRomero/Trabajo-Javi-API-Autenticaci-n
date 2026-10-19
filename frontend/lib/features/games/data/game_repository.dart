import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../shared/models/game.dart';

class GameRepository {
  final Dio _dio = ApiClient().dio;

  Future<List<Game>> getGroupGames(int groupId) async {
    final response = await _dio.get(ApiEndpoints.groupGames(groupId));
    final list = response.data as List<dynamic>;
    return list.map((g) => Game.fromJson(g as Map<String, dynamic>)).toList();
  }

  Future<List<BggSearchResult>> searchBgg(int groupId, String query) async {
    final response = await _dio.get(
      ApiEndpoints.searchBgg(groupId),
      queryParameters: {'query': query},
    );
    final list = response.data as List<dynamic>;
    return list.map((item) => BggSearchResult.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<Game> addGameFromBgg(int groupId, int bggId) async {
    final response = await _dio.post(
      ApiEndpoints.groupGames(groupId),
      data: {'bgg_id': bggId},
    );
    return Game.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> removeGame(int groupId, int gameId) async {
    await _dio.delete(ApiEndpoints.groupGame(groupId, gameId));
  }
}
