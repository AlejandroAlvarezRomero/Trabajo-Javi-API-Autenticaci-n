import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../shared/models/notification.dart';

class NotificationRepository {
  final Dio _dio = ApiClient().dio;

  Future<List<AppNotification>> getNotifications({bool? unreadOnly}) async {
    final response = await _dio.get(
      ApiEndpoints.notifications,
      queryParameters: {
        if (unreadOnly != null) 'unread_only': unreadOnly,
      },
    );
    final list = response.data as List<dynamic>;
    return list.map((n) => AppNotification.fromJson(n as Map<String, dynamic>)).toList();
  }

  Future<void> markRead(int id) async {
    await _dio.post(ApiEndpoints.markNotificationRead(id));
  }

  Future<void> markAllRead() async {
    await _dio.post(ApiEndpoints.markAllNotificationsRead);
  }
}
