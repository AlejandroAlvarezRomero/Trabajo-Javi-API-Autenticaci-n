import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/user_avatar.dart';
import '../../auth/providers/auth_provider.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  static const List<String> _presetAvatars = [
    'https://api.dicebear.com/7.x/adventurer/png?seed=warrior',
    'https://api.dicebear.com/7.x/adventurer/png?seed=mage',
    'https://api.dicebear.com/7.x/adventurer/png?seed=king',
    'https://api.dicebear.com/7.x/adventurer/png?seed=rogue',
    'https://api.dicebear.com/7.x/adventurer/png?seed=bard',
    'https://api.dicebear.com/7.x/bottts/png?seed=dice',
  ];

  void _showEditProfileDialog(BuildContext context, String currentDisplayName, String currentAvatarUrl) {
    final nameController = TextEditingController(text: currentDisplayName);
    final urlController = TextEditingController(text: currentAvatarUrl);
    String selectedUrl = currentAvatarUrl;
    bool saving = false;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (dialogCtx, setDialogState) {
            return AlertDialog(
              title: const Text('Editar Perfil'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Center(
                      child: UserAvatar(
                        avatarUrl: selectedUrl,
                        name: nameController.text.isNotEmpty ? nameController.text : 'Yo',
                        radius: 40,
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: nameController,
                      decoration: const InputDecoration(
                        labelText: 'Nombre público',
                        hintText: 'Tu nombre o apodo',
                        prefixIcon: Icon(Icons.badge),
                      ),
                      onChanged: (val) => setDialogState(() {}),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: urlController,
                      decoration: const InputDecoration(
                        labelText: 'URL de foto de perfil',
                        hintText: 'https://...',
                        prefixIcon: Icon(Icons.link),
                      ),
                      onChanged: (val) {
                        setDialogState(() {
                          selectedUrl = val.trim();
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'O elige un avatar temático:',
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppColors.textMuted),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _presetAvatars.map((preset) {
                        final isSelected = selectedUrl == preset;
                        return InkWell(
                          onTap: () {
                            setDialogState(() {
                              selectedUrl = preset;
                              urlController.text = preset;
                            });
                          },
                          borderRadius: BorderRadius.circular(24),
                          child: Container(
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: isSelected ? AppColors.primary : Colors.transparent,
                                width: 2.5,
                              ),
                            ),
                            child: UserAvatar(
                              avatarUrl: preset,
                              name: 'P',
                              radius: 20,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: saving ? null : () => Navigator.of(ctx).pop(),
                  child: const Text('Cancelar'),
                ),
                ElevatedButton(
                  onPressed: saving
                      ? null
                      : () async {
                          setDialogState(() => saving = true);
                          final ok = await ref.read(authProvider.notifier).updateProfile(
                                displayName: nameController.text.trim().isNotEmpty
                                    ? nameController.text.trim()
                                    : null,
                                avatarUrl: selectedUrl.trim().isNotEmpty ? selectedUrl.trim() : null,
                              );
                          if (dialogCtx.mounted) {
                            Navigator.of(ctx).pop();
                          }
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  ok ? 'Perfil actualizado con éxito' : 'Error al actualizar el perfil',
                                ),
                                backgroundColor: ok ? Colors.green : Colors.redAccent,
                              ),
                            );
                          }
                        },
                  child: saving
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Guardar'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final user = authState.user;

    if (user == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final displayName = user.displayName ?? user.username;
    final avatarUrl = user.avatarUrl ?? '';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi Perfil'),
        actions: [
          IconButton(
            tooltip: 'Editar Perfil',
            icon: const Icon(Icons.edit),
            onPressed: () => _showEditProfileDialog(context, user.displayName ?? '', avatarUrl),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Center(
              child: Column(
                children: [
                  Stack(
                    alignment: Alignment.bottomRight,
                    children: [
                      UserAvatar(
                        avatarUrl: user.avatarUrl,
                        name: displayName,
                        radius: 48,
                        onTap: () => _showEditProfileDialog(context, user.displayName ?? '', avatarUrl),
                      ),
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: AppColors.primary,
                          shape: BoxShape.circle,
                          border: Border.all(color: AppColors.cardDark, width: 2),
                        ),
                        child: const Icon(
                          Icons.camera_alt,
                          size: 16,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    displayName,
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '@${user.username} • ${user.email}',
                    style: const TextStyle(color: AppColors.textMuted),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.cardDark,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      'ROL: ${user.role.name}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppColors.rankOro,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.primaryLight,
                side: const BorderSide(color: AppColors.primaryLight),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              ),
              onPressed: () => _showEditProfileDialog(context, user.displayName ?? '', avatarUrl),
              icon: const Icon(Icons.edit),
              label: const Text('Editar Nombre y Foto de Perfil'),
            ),
            const SizedBox(height: 24),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.military_tech, color: Colors.amber),
                    title: const Text('Mis Logros e Insignias'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('/achievements'),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.calendar_month, color: AppColors.primary),
                    title: const Text('Miembro desde'),
                    trailing: Text(
                      DateFormat('dd/MM/yyyy').format(user.createdAt),
                      style: const TextStyle(color: AppColors.textMuted),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.redAccent,
                  side: const BorderSide(color: Colors.redAccent),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                onPressed: () async {
                  await ref.read(authProvider.notifier).logout();
                  if (context.mounted) {
                    context.go('/login');
                  }
                },
                icon: const Icon(Icons.logout),
                label: const Text('Cerrar Sesión'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
