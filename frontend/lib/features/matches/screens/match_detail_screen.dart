import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/models/match.dart';
import '../../../shared/widgets/user_avatar.dart';
import '../../auth/providers/auth_provider.dart';

import '../../groups/providers/groups_provider.dart';
import '../providers/matches_provider.dart';

class MatchDetailScreen extends ConsumerStatefulWidget {
  final int groupId;
  final int matchId;

  const MatchDetailScreen({
    super.key,
    required this.groupId,
    required this.matchId,
  });

  @override
  ConsumerState<MatchDetailScreen> createState() => _MatchDetailScreenState();
}

class _MatchDetailScreenState extends ConsumerState<MatchDetailScreen> {
  Match? _match;
  bool _loading = true;
  String? _error;
  bool _acting = false;

  @override
  void initState() {
    super.initState();
    _loadMatch();
  }

  Future<void> _loadMatch() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final repo = ref.read(matchRepositoryProvider);
      final match = await repo.getMatch(widget.groupId, widget.matchId);
      setState(() {
        _match = match;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Error cargando partida: $e';
        _loading = false;
      });
    }
  }

  Future<void> _confirm() async {
    setState(() => _acting = true);
    try {
      await ref.read(matchRepositoryProvider).confirmMatch(widget.groupId, widget.matchId);
      ref.invalidate(groupMatchesProvider(widget.groupId));
      await _loadMatch();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Has confirmado el resultado')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al confirmar: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _reject() async {
    setState(() => _acting = true);
    try {
      await ref.read(matchRepositoryProvider).rejectMatch(widget.groupId, widget.matchId);
      ref.invalidate(groupMatchesProvider(widget.groupId));
      await _loadMatch();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Has rechazado el resultado')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al rechazar: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  Future<void> _cancel() async {
    setState(() => _acting = true);
    try {
      await ref.read(matchRepositoryProvider).cancelMatch(widget.groupId, widget.matchId);
      ref.invalidate(groupMatchesProvider(widget.groupId));
      await _loadMatch();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Partida cancelada por moderación')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error al cancelar: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _acting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Detalle de Partida')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_error != null || _match == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Detalle de Partida')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error ?? 'No encontrada'),
              const SizedBox(height: 12),
              ElevatedButton(onPressed: _loadMatch, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    final match = _match!;
    final currentUser = ref.watch(authProvider).user;
    final groupAsync = ref.watch(groupDetailProvider(widget.groupId));
    final isManager = groupAsync.value?.isManager ?? false;

    // Verificar si el usuario actual tiene confirmación pendiente
    final myConfirmation = currentUser != null
        ? match.confirmations.where((c) => c.userId == currentUser.id).firstOrNull
        : null;
    final canConfirmOrReject = match.isPending && myConfirmation != null && myConfirmation.isPending;

    Color statusColor = Colors.orange;
    if (match.isConfirmed) statusColor = Colors.green;
    if (match.isRejected) statusColor = Colors.redAccent;
    if (match.isCancelled) statusColor = Colors.grey;

    return Scaffold(
      appBar: AppBar(
        title: Text(match.gameName ?? 'Partida #${match.id}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _acting ? null : _loadMatch,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          match.gameName ?? 'Juego #${match.gameId}',
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: statusColor.withOpacity(0.18),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: statusColor.withOpacity(0.5)),
                          ),
                          child: Text(
                            match.status,
                            style: TextStyle(
                              color: statusColor,
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        const Icon(Icons.calendar_today, size: 16, color: AppColors.textMuted),
                        const SizedBox(width: 6),
                        Text(
                          DateFormat('dd/MM/yyyy HH:mm').format(match.playedAt),
                          style: const TextStyle(color: AppColors.textMuted),
                        ),
                        if (match.durationMinutes != null) ...[
                          const SizedBox(width: 16),
                          const Icon(Icons.timer_outlined, size: 16, color: AppColors.textMuted),
                          const SizedBox(width: 6),
                          Text(
                            '${match.durationMinutes} min',
                            style: const TextStyle(color: AppColors.textMuted),
                          ),
                        ],
                      ],
                    ),
                    if (match.notes != null && match.notes!.isNotEmpty) ...[
                      const Divider(height: 24),
                      Text(
                        'Notas: ${match.notes!}',
                        style: const TextStyle(fontStyle: FontStyle.italic),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Participantes & Resultados
            const Text(
              'Participantes y ELO',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Card(
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: match.participants.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final p = match.participants[index];
                  final isWinner = p.userId == match.winnerId;

                  return ListTile(
                    leading: Stack(
                      alignment: Alignment.bottomRight,
                      children: [
                        UserAvatar(
                          avatarUrl: p.avatarUrl,
                          name: p.displayName ?? p.username,
                          radius: 20,
                        ),
                        if (isWinner)
                          const CircleAvatar(
                            radius: 8,
                            backgroundColor: Colors.amber,
                            child: Icon(Icons.star, size: 10, color: Colors.black),
                          ),
                      ],
                    ),
                    title: Row(
                      children: [
                        Text(
                          p.displayName ?? p.username,
                          style: TextStyle(
                            fontWeight: isWinner ? FontWeight.bold : FontWeight.normal,
                          ),
                        ),
                        if (isWinner) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.amber.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text(
                              'GANADOR',
                              style: TextStyle(fontSize: 10, color: Colors.amber, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ],
                    ),
                    trailing: p.eloDelta != null
                        ? Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: p.eloDelta! >= 0
                                  ? Colors.green.withOpacity(0.15)
                                  : Colors.red.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              p.eloDelta! >= 0 ? '+${p.eloDelta}' : '${p.eloDelta}',
                              style: TextStyle(
                                color: p.eloDelta! >= 0 ? Colors.green : Colors.redAccent,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          )
                        : const Text('Pendiente', style: TextStyle(color: AppColors.textMuted)),
                  );
                },
              ),
            ),
            const SizedBox(height: 20),

            // Confirmaciones
            const Text(
              'Estado de Verificación',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Card(
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: match.confirmations.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final c = match.confirmations[index];
                  Widget trailingIcon;
                  String statusText;
                  Color color;

                  if (c.confirmed == true) {
                    trailingIcon = const Icon(Icons.check_circle, color: Colors.green);
                    statusText = 'Confirmada';
                    color = Colors.green;
                  } else if (c.confirmed == false) {
                    trailingIcon = const Icon(Icons.cancel, color: Colors.redAccent);
                    statusText = 'Rechazada';
                    color = Colors.redAccent;
                  } else {
                    trailingIcon = const Icon(Icons.hourglass_empty, color: Colors.orange);
                    statusText = 'Pendiente de confirmación';
                    color = Colors.orange;
                  }

                  return ListTile(
                    leading: UserAvatar(
                      avatarUrl: c.avatarUrl,
                      name: c.displayName ?? c.username,
                      radius: 18,
                    ),
                    title: Text(c.displayName ?? c.username),
                    subtitle: Text(statusText, style: TextStyle(color: color, fontSize: 12)),
                    trailing: trailingIcon,
                  );

                },
              ),
            ),
            const SizedBox(height: 24),

            // Botones de acción si canConfirmOrReject
            if (canConfirmOrReject) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surfaceDark,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.primary.withOpacity(0.4)),
                ),
                child: Column(
                  children: [
                    const Text(
                      'Tu confirmación es necesaria para verificar esta partida y aplicar el ELO.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green,
                              foregroundColor: Colors.white,
                            ),
                            onPressed: _acting ? null : _confirm,
                            icon: const Icon(Icons.check),
                            label: const Text('Confirmar'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: OutlinedButton.icon(
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.redAccent,
                              side: const BorderSide(color: Colors.redAccent),
                            ),
                            onPressed: _acting ? null : _reject,
                            icon: const Icon(Icons.close),
                            label: const Text('Rechazar'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Botón de moderador para cancelar partida si está PENDING
            if (isManager && match.isPending) ...[
              SizedBox(
                width: double.infinity,
                child: TextButton.icon(
                  style: TextButton.styleFrom(foregroundColor: Colors.redAccent),
                  onPressed: _acting ? null : _cancel,
                  icon: const Icon(Icons.delete_outline),
                  label: const Text('Cancelar partida (como Moderador)'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
