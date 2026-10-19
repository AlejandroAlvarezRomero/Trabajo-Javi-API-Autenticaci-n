import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/notification.dart';
import '../data/notification_repository.dart';

final notificationRepositoryProvider = Provider((ref) => NotificationRepository());

final notificationsProvider =
    AsyncNotifierProvider<NotificationsNotifier, List<AppNotification>>(
  NotificationsNotifier.new,
);

class NotificationsNotifier extends AsyncNotifier<List<AppNotification>> {
  @override
  Future<List<AppNotification>> build() async {
    return ref.watch(notificationRepositoryProvider).getNotifications();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
        () => ref.read(notificationRepositoryProvider).getNotifications());
  }

  Future<void> markRead(int id) async {
    await ref.read(notificationRepositoryProvider).markRead(id);
    await refresh();
  }

  Future<void> markAllRead() async {
    await ref.read(notificationRepositoryProvider).markAllRead();
    await refresh();
  }
}
