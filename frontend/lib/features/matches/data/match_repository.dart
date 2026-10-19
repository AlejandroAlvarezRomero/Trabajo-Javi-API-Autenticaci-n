import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../shared/models/match.dart';

class MatchRepository {
  final Dio _dio = ApiClient().dio;

  Future<List<Match>> getGroupMatches(
    int groupId, {
    String? status,
    int? limit,
  }) async {
    final response = await _dio.get(
      ApiEndpoints.groupMatches(groupId),
      queryParameters: {
        if (status != null) 'status': status,
        if (limit != null) 'limit': limit,
      },
    );
    final list = response.data as List<dynamic>;
    return list.map((m) => Match.fromJson(m as Map<String, dynamic>)).toList();
  }

  Future<Match> getMatch(int groupId, int matchId) async {
    final response = await _dio.get(ApiEndpoints.groupMatch(groupId, matchId));
    return Match.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Match> createMatch(int groupId, MatchCreate data) async {
    final response = await _dio.post(
      ApiEndpoints.groupMatches(groupId),
      data: data.toJson(),
    );
    return Match.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Match> confirmMatch(int groupId, int matchId) async {
    final response = await _dio.post(ApiEndpoints.confirmMatch(groupId, matchId));
    return Match.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Match> rejectMatch(int groupId, int matchId) async {
    final response = await _dio.post(ApiEndpoints.rejectMatch(groupId, matchId));
    return Match.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Match> cancelMatch(int groupId, int matchId) async {
    final response = await _dio.post(ApiEndpoints.cancelMatch(groupId, matchId));
    return Match.fromJson(response.data as Map<String, dynamic>);
  }
}
