import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/storage/token_storage.dart';
import '../../../shared/models/user.dart';

class AuthRepository {
  final Dio _dio = ApiClient().dio;

  Future<User> register({
    required String email,
    required String username,
    required String password,
  }) async {
    final response = await _dio.post(
      ApiEndpoints.register,
      data: {
        'email': email,
        'username': username,
        'password': password,
      },
    );
    return User.fromJson(response.data as Map<String, dynamic>);
  }

  Future<TokenResponse> login({
    required String email,
    required String password,
  }) async {
    final response = await _dio.post(
      ApiEndpoints.login,
      data: {
        'email': email,
        'password': password,
      },
    );
    final tokenResp = TokenResponse.fromJson(response.data as Map<String, dynamic>);
    await TokenStorage.saveAccessToken(tokenResp.accessToken);
    return tokenResp;
  }

  Future<User> getMe() async {
    final response = await _dio.get(ApiEndpoints.me);
    return User.fromJson(response.data as Map<String, dynamic>);
  }

  Future<User> updateProfile({
    String? displayName,
    String? avatarUrl,
  }) async {
    final response = await _dio.patch(
      ApiEndpoints.me,
      data: {
        if (displayName != null) 'display_name': displayName,
        if (avatarUrl != null) 'avatar_url': avatarUrl,
      },
    );
    return User.fromJson(response.data as Map<String, dynamic>);
  }

  Future<User> uploadAvatar(List<int> bytes, String filename) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: filename),
    });
    final response = await _dio.post(
      ApiEndpoints.avatar,
      data: formData,
    );
    return User.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> forgotPassword(String email) async {
    final response = await _dio.post(
      ApiEndpoints.forgotPassword,
      data: {'email': email},
    );
    return response.data as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> resetPassword({
    required String token,
    required String newPassword,
  }) async {
    final response = await _dio.post(
      ApiEndpoints.resetPassword,
      data: {
        'token': token,
        'new_password': newPassword,
      },
    );
    return response.data as Map<String, dynamic>;
  }

  Future<void> logout() async {
    try {
      await _dio.post(ApiEndpoints.logout);
    } catch (_) {}
    await TokenStorage.clear();
  }
}

