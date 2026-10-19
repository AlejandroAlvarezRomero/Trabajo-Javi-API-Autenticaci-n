import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../shared/models/group.dart';
import '../../../shared/models/stats.dart';

class StatsRepository {
  final Dio _dio = ApiClient().dio;

  Future<Leaderboard> getLeaderboard(int groupId) async {
    final response = await _dio.get(ApiEndpoints.leaderboard(groupId));
    return Leaderboard.fromJson(response.data as Map<String, dynamic>);
  }

  Future<GroupStats> getMyStats(int groupId) async {
    final response = await _dio.get(ApiEndpoints.myStats(groupId));
    return GroupStats.fromJson(response.data as Map<String, dynamic>);
  }

  Future<GroupStats> getUserStats(int groupId, int userId) async {
    final response = await _dio.get(ApiEndpoints.userStats(groupId, userId));
    return GroupStats.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<Season>> getGroupSeasons(int groupId) async {
    final response = await _dio.get(ApiEndpoints.groupSeasons(groupId));
    final list = response.data as List<dynamic>;
    return list.map((s) => Season.fromJson(s as Map<String, dynamic>)).toList();
  }

  Future<Season> rolloverSeason(int groupId) async {
    final response = await _dio.post(ApiEndpoints.seasonRollover(groupId));
    return Season.fromJson(response.data as Map<String, dynamic>);
  }
}
