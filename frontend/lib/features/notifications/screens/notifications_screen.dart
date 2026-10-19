import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/notifications_provider.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(notificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notificaciones'),
        actions: [
          IconButton(
            tooltip: 'Marcar todas como leídas',
            icon: const Icon(Icons.done_all),
            onPressed: () async {
              await ref.read(notificationsProvider.notifier).markAllRead();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Todas marcadas como leídas')),
                );
              }
            },
          ),
        ],
      ),
      body: notificationsAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.notifications_none, size: 64, color: AppColors.textMuted),
                  SizedBox(height: 12),
                  Text('No tienes notificaciones pendientes',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => ref.read(notificationsProvider.notifier).refresh(),
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: notifications.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final item = notifications[index];

                IconData icon = Icons.notifications;
                Color iconColor = AppColors.primary;
                if (item.type.contains('CONFIRMATION')) {
                  icon = Icons.rule;
                  iconColor = Colors.orange;
                } else if (item.type.contains('ACHIEVEMENT')) {
                  icon = Icons.military_tech;
                  iconColor = Colors.amber;
                }

                return Card(
                  color: item.isRead ? AppColors.surfaceDark : AppColors.cardDark.withOpacity(0.5),
                  child: ListTile(
                    onTap: () {
                      if (!item.isRead) {
                        ref.read(notificationsProvider.notifier).markRead(item.id);
                      }
                    },
                    leading: CircleAvatar(
                      backgroundColor: iconColor.withOpacity(0.2),
                      child: Icon(icon, color: iconColor),
                    ),
                    title: Text(
                      item.title,
                      style: TextStyle(
                        fontWeight: item.isRead ? FontWeight.normal : FontWeight.bold,
                      ),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (item.body != null) ...[
                          const SizedBox(height: 4),
                          Text(item.body!),
                        ],
                        const SizedBox(height: 4),
                        Text(
                          DateFormat('dd/MM HH:mm').format(item.createdAt),
                          style: const TextStyle(color: AppColors.textMuted, fontSize: 11),
                        ),
                      ],
                    ),
                    trailing: !item.isRead
                        ? Container(
                            width: 8,
                            height: 8,
                            decoration: const BoxDecoration(
                              color: AppColors.primaryLight,
                              shape: BoxShape.circle,
                            ),
                          )
                        : null,
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error cargando notificaciones: $e')),
      ),
    );
  }
}
