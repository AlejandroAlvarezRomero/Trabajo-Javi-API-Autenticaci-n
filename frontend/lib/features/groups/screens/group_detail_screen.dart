import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/elo_badge.dart';
import '../../../shared/widgets/user_avatar.dart';
import '../../auth/providers/auth_provider.dart';
import '../../games/providers/games_provider.dart';
import '../../games/screens/bgg_search_dialog.dart';
import '../../matches/providers/matches_provider.dart';
import '../../stats/providers/stats_provider.dart';
import '../providers/groups_provider.dart';


class GroupDetailScreen extends ConsumerStatefulWidget {
  final int groupId;

  const GroupDetailScreen({super.key, required this.groupId});

  @override
  ConsumerState<GroupDetailScreen> createState() => _GroupDetailScreenState();
}

class _GroupDetailScreenState extends ConsumerState<GroupDetailScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _showRolloverDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Iniciar Nueva Temporada'),
        content: const Text(
          'Al cerrar la temporada actual, se guardará el histórico y se aplicará '
          'un soft reset del 50% al ELO de todos los jugadores hacia la media (1200). '
          '¿Deseas continuar?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
            onPressed: () async {
              Navigator.pop(ctx);
              try {
                final repo = ref.read(statsRepositoryProvider);
                await repo.rolloverSeason(widget.groupId);
                ref.invalidate(leaderboardProvider(widget.groupId));
                ref.invalidate(seasonsProvider(widget.groupId));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('¡Nueva temporada iniciada con éxito!')),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Error al cambiar de temporada: $e')),
                  );
                }
              }
            },
            child: const Text('Confirmar Rollover'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final groupAsync = ref.watch(groupDetailProvider(widget.groupId));

    return groupAsync.when(
      data: (group) {
        final isManager = group.isManager;

        return Scaffold(
          appBar: AppBar(
            title: Text(group.name),
            bottom: TabBar(
              controller: _tabController,
              isScrollable: true,
              indicatorColor: AppColors.primaryLight,
              tabs: const [
                Tab(icon: Icon(Icons.sports_esports), text: 'Partidas'),
                Tab(icon: Icon(Icons.leaderboard), text: 'Clasificación'),
                Tab(icon: Icon(Icons.casino), text: 'Catálogo'),
                Tab(icon: Icon(Icons.people), text: 'Miembros'),
              ],
            ),
            actions: [
              IconButton(
                tooltip: 'Código: ${group.inviteCode}',
                icon: const Icon(Icons.qr_code),
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text('Código de Invitación'),
                      content: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text('Comparte este código con tus amigos para que se unan:'),
                          const SizedBox(height: 16),
                          SelectableText(
                            group.inviteCode,
                            style: const TextStyle(
                              fontSize: 32,
                              fontWeight: FontWeight.bold,
                              letterSpacing: 4,
                              color: AppColors.primaryLight,
                            ),
                          ),
                        ],
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx),
                          child: const Text('Cerrar'),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
          body: TabBarView(
            controller: _tabController,
            children: [
              _MatchesTab(groupId: widget.groupId),
              _LeaderboardTab(
                groupId: widget.groupId,
                isManager: isManager,
                onRollover: () => _showRolloverDialog(context, ref),
              ),
              _GamesTab(groupId: widget.groupId, isManager: isManager),
              _MembersTab(groupId: widget.groupId, isManager: isManager),
            ],
          ),
          floatingActionButton: _tabController.index == 0
              ? FloatingActionButton.extended(
                  onPressed: () => context.push('/groups/${widget.groupId}/matches/new'),
                  icon: const Icon(Icons.add),
                  label: const Text('Nueva Partida'),
                )
              : null,
        );
      },
      loading: () => Scaffold(
        appBar: AppBar(title: const Text('Cargando grupo...')),
        body: const Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Scaffold(
        appBar: AppBar(title: const Text('Error')),
        body: Center(child: Text('Error cargando grupo: $e')),
      ),
    );
  }
}

// -----------------------------------------------------------------------------
// TAB 1: PARTIDAS
// -----------------------------------------------------------------------------
class _MatchesTab extends ConsumerWidget {
  final int groupId;

  const _MatchesTab({required this.groupId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final matchesAsync = ref.watch(groupMatchesProvider(groupId));

    return matchesAsync.when(
      data: (matches) {
        if (matches.isEmpty) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.history_toggle_off, size: 64, color: AppColors.textMuted),
                const SizedBox(height: 12),
                const Text('No hay partidas registradas aún',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: () => context.push('/groups/$groupId/matches/new'),
                  icon: const Icon(Icons.add),
                  label: const Text('Registrar Primera Partida'),
                ),
              ],
            ),
          );
        }

        return RefreshIndicator(
          onRefresh: () async => ref.invalidate(groupMatchesProvider(groupId)),
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: matches.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final match = matches[index];
              Color statusColor = Colors.orange;
              if (match.isConfirmed) statusColor = Colors.green;
              if (match.isRejected) statusColor = Colors.redAccent;
              if (match.isCancelled) statusColor = Colors.grey;

              final winner = match.participants
                  .where((p) => p.userId == match.winnerId)
                  .firstOrNull;

              return Card(
                child: ListTile(
                  onTap: () => context.push('/groups/$groupId/matches/${match.id}'),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  leading: CircleAvatar(
                    backgroundColor: statusColor.withOpacity(0.18),
                    child: Icon(
                      match.isConfirmed
                          ? Icons.emoji_events
                          : match.isPending
                              ? Icons.hourglass_top
                              : Icons.cancel,
                      color: statusColor,
                    ),
                  ),
                  title: Row(
                    children: [
                      Text(
                        match.gameName ?? 'Partida #${match.id}',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: statusColor.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          match.status,
                          style: TextStyle(
                            color: statusColor,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 4.0),
                    child: Text(
                      'Ganador: ${winner?.username ?? 'ID ${match.winnerId}'} • '
                      '${DateFormat('dd/MM HH:mm').format(match.playedAt)}',
                      style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                    ),
                  ),
                  trailing: const Icon(Icons.chevron_right, color: AppColors.textMuted),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error cargando partidas: $e')),
    );
  }
}

// -----------------------------------------------------------------------------
// TAB 2: CLASIFICACIÓN (LEADERBOARD)
// -----------------------------------------------------------------------------
class _LeaderboardTab extends ConsumerWidget {
  final int groupId;
  final bool isManager;
  final VoidCallback onRollover;

  const _LeaderboardTab({
    required this.groupId,
    required this.isManager,
    required this.onRollover,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final leaderboardAsync = ref.watch(leaderboardProvider(groupId));

    return leaderboardAsync.when(
      data: (lb) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Season header card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            lb.season.name,
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Finaliza: ${DateFormat('dd/MM/yyyy').format(lb.season.endDate)}',
                            style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                          ),
                        ],
                      ),
                      if (isManager)
                        OutlinedButton.icon(
                          onPressed: onRollover,
                          icon: const Icon(Icons.autorenew, size: 16),
                          label: const Text('Cerrar Temporada'),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              if (lb.entries.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(32.0),
                  child: Center(
                    child: Text('Aún no hay puntuaciones en esta temporada'),
                  ),
                )
              else
                Card(
                  child: ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: lb.entries.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final entry = lb.entries[index];
                      final position = index + 1;

                      return ListTile(
                        leading: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 22,
                              child: Text(
                                '$position',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                  color: position == 1
                                      ? Colors.amber
                                      : position == 2
                                          ? Colors.grey[300]
                                          : position == 3
                                              ? Colors.brown[300]
                                              : AppColors.textMuted,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            UserAvatar(
                              avatarUrl: entry.avatarUrl,
                              name: entry.displayName ?? entry.username,
                              radius: 18,
                            ),
                          ],
                        ),

                        title: Text(
                          entry.displayName ?? entry.username,
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        subtitle: Text(
                          '${entry.wins}V / ${entry.losses}D (${entry.winRate.toStringAsFixed(0)}%) • ${entry.gamesPlayed} partidas',
                          style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
                        ),
                        trailing: EloBadge(elo: entry.elo, rank: entry.rank, compact: true),
                      );
                    },
                  ),
                ),
            ],
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error cargando clasificación: $e')),
    );
  }
}

// -----------------------------------------------------------------------------
// TAB 3: CATÁLOGO DE JUEGOS
// -----------------------------------------------------------------------------
class _GamesTab extends ConsumerWidget {
  final int groupId;
  final bool isManager;

  const _GamesTab({required this.groupId, required this.isManager});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final gamesAsync = ref.watch(groupGamesProvider(groupId));

    return gamesAsync.when(
      data: (games) {
        return Scaffold(
          body: games.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.casino_outlined, size: 64, color: AppColors.textMuted),
                      const SizedBox(height: 12),
                      const Text('El catálogo está vacío',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      if (isManager) ...[
                        const Text('Busca juegos en BoardGameGeek o precarga los más populares'),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 12,
                          runSpacing: 8,
                          alignment: WrapAlignment.center,
                          children: [
                            ElevatedButton.icon(
                              onPressed: () {
                                showDialog(
                                  context: context,
                                  builder: (_) => BggSearchDialog(groupId: groupId),
                                );
                              },
                              icon: const Icon(Icons.search),
                              label: const Text('Buscar en BGG'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () async {
                                await ref.read(groupRepositoryProvider).seedPopularGames(groupId);
                                ref.invalidate(groupGamesProvider(groupId));
                                if (context.mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Juegos populares precargados con éxito')),
                                  );
                                }
                              },
                              icon: const Icon(Icons.auto_awesome),
                              label: const Text('Precargar Populares'),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: games.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final game = games[index];

                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            if (game.thumbnailUrl != null)
                              ClipRRect(
                                borderRadius: BorderRadius.circular(8),
                                child: Image.network(
                                  game.thumbnailUrl!,
                                  width: 60,
                                  height: 60,
                                  fit: BoxFit.cover,
                                  errorBuilder: (context, error, stackTrace) =>
                                      const Icon(Icons.casino),
                                ),
                              )
                            else
                              Container(
                                width: 60,
                                height: 60,
                                decoration: BoxDecoration(
                                  color: AppColors.cardDark,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Icon(Icons.casino, color: AppColors.textMuted),
                              ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    game.name,
                                    style: const TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Row(
                                    children: [
                                      if (game.playersSpan.isNotEmpty) ...[
                                        const Icon(Icons.people_outline, size: 14, color: AppColors.textMuted),
                                        const SizedBox(width: 4),
                                        Text(game.playersSpan, style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                                        const SizedBox(width: 12),
                                      ],
                                      if (game.avgPlaytimeMinutes != null) ...[
                                        const Icon(Icons.timer_outlined, size: 14, color: AppColors.textMuted),
                                        const SizedBox(width: 4),
                                        Text('${game.avgPlaytimeMinutes} min', style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                                      ],
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
          floatingActionButton: isManager
              ? Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    FloatingActionButton.small(
                      heroTag: 'seed_popular_$groupId',
                      tooltip: 'Precargar juegos populares',
                      onPressed: () async {
                        await ref.read(groupRepositoryProvider).seedPopularGames(groupId);
                        ref.invalidate(groupGamesProvider(groupId));
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Catálogo precargado con juegos populares')),
                          );
                        }
                      },
                      child: const Icon(Icons.auto_awesome),
                    ),
                    const SizedBox(height: 8),
                    FloatingActionButton.extended(
                      heroTag: 'add_bgg_$groupId',
                      onPressed: () {
                        showDialog(
                          context: context,
                          builder: (_) => BggSearchDialog(groupId: groupId),
                        );
                      },
                      icon: const Icon(Icons.search),
                      label: const Text('Añadir Juego BGG'),
                    ),
                  ],
                )
              : null,
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error cargando catálogo: $e')),
    );
  }
}

// -----------------------------------------------------------------------------
// TAB 4: MIEMBROS
// -----------------------------------------------------------------------------
class _MembersTab extends ConsumerWidget {
  final int groupId;
  final bool isManager;

  const _MembersTab({required this.groupId, required this.isManager});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final membersAsync = ref.watch(groupMembersProvider(groupId));
    final groupDetail = ref.watch(groupDetailProvider(groupId)).value;
    final currentUser = ref.watch(authProvider).user;
    final isOwner = groupDetail != null && currentUser != null && groupDetail.ownerId == currentUser.id;

    return membersAsync.when(
      data: (members) {
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: members.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final member = members[index];
            final memberIsManager = member.isManager;
            final isSelf = currentUser != null && member.userId == currentUser.id;

            return Card(
              child: ListTile(
                leading: UserAvatar(
                  avatarUrl: member.avatarUrl,
                  name: member.displayName ?? member.username,
                  radius: 20,
                ),
                title: Text(
                  member.displayName ?? member.username,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                subtitle: Text('@${member.username} • Miembro desde ${DateFormat('dd/MM/yyyy').format(member.joinedAt)}'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppColors.cardDark,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        member.role,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: memberIsManager ? AppColors.primaryLight : AppColors.textMuted,
                        ),
                      ),
                    ),
                    if (isOwner && !isSelf) ...[
                      const SizedBox(width: 4),
                      PopupMenuButton<String>(
                        icon: const Icon(Icons.more_vert, size: 20),
                        onSelected: (action) async {
                          if (action == 'transfer') {
                            final confirm = await showDialog<bool>(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                title: const Text('Transferir Propiedad'),
                                content: Text(
                                  '¿Estás seguro de transferir la propiedad del grupo a ${member.displayName ?? member.username}? Dejarás de ser el propietario.',
                                ),
                                actions: [
                                  TextButton(
                                    onPressed: () => Navigator.of(ctx).pop(false),
                                    child: const Text('Cancelar'),
                                  ),
                                  ElevatedButton(
                                    style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                                    onPressed: () => Navigator.of(ctx).pop(true),
                                    child: const Text('Transferir'),
                                  ),
                                ],
                              ),
                            );
                            if (confirm == true) {
                              await ref.read(groupRepositoryProvider).transferOwnership(groupId, member.userId);
                              ref.invalidate(groupDetailProvider(groupId));
                              ref.invalidate(groupMembersProvider(groupId));
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Propiedad transferida con éxito')),
                                );
                              }
                            }
                          } else if (action == 'toggle_role') {
                            final newRole = memberIsManager ? 'MEMBER' : 'MANAGER';
                            await ref.read(groupRepositoryProvider).updateMemberRole(groupId, member.userId, newRole);
                            ref.invalidate(groupMembersProvider(groupId));
                          } else if (action == 'kick') {
                            await ref.read(groupRepositoryProvider).kickMember(groupId, member.userId);
                            ref.invalidate(groupMembersProvider(groupId));
                          }
                        },
                        itemBuilder: (ctx) => [
                          PopupMenuItem(
                            value: 'transfer',
                            child: const Row(
                              children: [
                                Icon(Icons.admin_panel_settings, color: AppColors.primaryLight, size: 18),
                                SizedBox(width: 8),
                                Text('Hacer Propietario'),
                              ],
                            ),
                          ),
                          PopupMenuItem(
                            value: 'toggle_role',
                            child: Row(
                              children: [
                                Icon(memberIsManager ? Icons.person : Icons.star, size: 18),
                                const SizedBox(width: 8),
                                Text(memberIsManager ? 'Degradar a Miembro' : 'Promover a Gestor'),
                              ],
                            ),
                          ),
                          const PopupMenuItem(
                            value: 'kick',
                            child: Row(
                              children: [
                                Icon(Icons.person_remove, color: Colors.redAccent, size: 18),
                                SizedBox(width: 8),
                                Text('Expulsar', style: TextStyle(color: Colors.redAccent)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error cargando miembros: $e')),
    );
  }
}

