import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../shared/models/achievement.dart';

class AchievementRepository {
  final Dio _dio = ApiClient().dio;

  Future<List<Achievement>> getAllAchievements() async {
    final response = await _dio.get(ApiEndpoints.achievements);
    final list = response.data as List<dynamic>;
    return list.map((a) => Achievement.fromJson(a as Map<String, dynamic>)).toList();
  }

  Future<List<UserAchievement>> getMyAchievements() async {
    final response = await _dio.get(ApiEndpoints.myAchievements);
    final list = response.data as List<dynamic>;
    return list.map((ua) => UserAchievement.fromJson(ua as Map<String, dynamic>)).toList();
  }
}
