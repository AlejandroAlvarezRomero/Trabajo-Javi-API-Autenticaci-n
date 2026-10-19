import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/achievements_provider.dart';

class AchievementsScreen extends ConsumerWidget {
  const AchievementsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final allAsync = ref.watch(allAchievementsProvider);
    final myAsync = ref.watch(myAchievementsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Logros e Insignias'),
      ),
      body: myAsync.when(
        data: (myAchievements) {
          final unlockedCodes = myAchievements.map((ua) => ua.achievement.code).toSet();

          return allAsync.when(
            data: (allAchievements) {
              return ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: allAchievements.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final ach = allAchievements[index];
                  final isUnlocked = unlockedCodes.contains(ach.code);
                  final userAch = isUnlocked
                      ? myAchievements.firstWhere((ua) => ua.achievement.code == ach.code)
                      : null;

                  return Card(
                    color: isUnlocked ? AppColors.surfaceDark : AppColors.cardDark.withOpacity(0.3),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Row(
                        children: [
                          Container(
                            width: 52,
                            height: 52,
                            decoration: BoxDecoration(
                              color: isUnlocked
                                  ? Colors.amber.withOpacity(0.2)
                                  : AppColors.cardDark.withOpacity(0.5),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: isUnlocked ? Colors.amber : Colors.transparent,
                              ),
                            ),
                            child: Icon(
                              Icons.military_tech,
                              size: 32,
                              color: isUnlocked ? Colors.amber : AppColors.textMuted,
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      ach.name,
                                      style: TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                        color: isUnlocked ? AppColors.textLight : AppColors.textMuted,
                                      ),
                                    ),
                                    if (isUnlocked) ...[
                                      const SizedBox(width: 8),
                                      const Icon(Icons.check_circle, color: Colors.green, size: 16),
                                    ],
                                  ],
                                ),
                                if (ach.description != null) ...[
                                  const SizedBox(height: 4),
                                  Text(
                                    ach.description!,
                                    style: const TextStyle(
                                      color: AppColors.textMuted,
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                                if (userAch != null) ...[
                                  const SizedBox(height: 6),
                                  Text(
                                    'Desbloqueado el ${DateFormat('dd/MM/yyyy').format(userAch.unlockedAt)}',
                                    style: const TextStyle(
                                      color: Colors.amber,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              );
            },
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('Error: $e')),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}
