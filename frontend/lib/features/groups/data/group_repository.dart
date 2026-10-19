import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../shared/models/group.dart';

class GroupRepository {
  final Dio _dio = ApiClient().dio;

  Future<List<Group>> getMyGroups() async {
    final response = await _dio.get(ApiEndpoints.groups);
    final list = response.data as List<dynamic>;
    return list.map((g) => Group.fromJson(g as Map<String, dynamic>)).toList();
  }

  Future<Group> createGroup(String name, String? description) async {
    final response = await _dio.post(
      ApiEndpoints.groups,
      data: {
        'name': name,
        'description': description,
      },
    );
    return Group.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Group> joinGroup(String inviteCode) async {
    final response = await _dio.post(
      ApiEndpoints.joinGroup,
      data: {'invite_code': inviteCode},
    );
    return Group.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Group> getGroup(int id) async {
    final response = await _dio.get(ApiEndpoints.groupDetail(id));
    return Group.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<Member>> getMembers(int groupId) async {
    final response = await _dio.get(ApiEndpoints.groupMembers(groupId));
    final list = response.data as List<dynamic>;
    return list.map((m) => Member.fromJson(m as Map<String, dynamic>)).toList();
  }

  Future<void> updateMemberRole(int groupId, int userId, String role) async {
    await _dio.patch(
      ApiEndpoints.groupMember(groupId, userId),
      data: {'role': role},
    );
  }

  Future<void> kickMember(int groupId, int userId) async {
    await _dio.delete(ApiEndpoints.groupMember(groupId, userId));
  }

  Future<void> leaveGroup(int groupId) async {
    await _dio.post(ApiEndpoints.leaveGroup(groupId));
  }

  Future<void> deleteGroup(int groupId) async {
    await _dio.delete(ApiEndpoints.groupDetail(groupId));
  }

  Future<void> transferOwnership(int groupId, int newOwnerId) async {
    await _dio.post(
      ApiEndpoints.transferOwnership(groupId),
      data: {'new_owner_id': newOwnerId},
    );
  }

  Future<void> seedPopularGames(int groupId) async {
    await _dio.post(ApiEndpoints.seedPopularGames(groupId));
  }
}

