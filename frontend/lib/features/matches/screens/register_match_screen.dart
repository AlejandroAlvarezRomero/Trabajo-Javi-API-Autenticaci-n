import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/models/game.dart';
import '../../../shared/models/match.dart';
import '../../auth/providers/auth_provider.dart';
import '../../games/providers/games_provider.dart';
import '../../groups/providers/groups_provider.dart';
import '../providers/matches_provider.dart';

class RegisterMatchScreen extends ConsumerStatefulWidget {
  final int groupId;

  const RegisterMatchScreen({super.key, required this.groupId});

  @override
  ConsumerState<RegisterMatchScreen> createState() => _RegisterMatchScreenState();
}

class _RegisterMatchScreenState extends ConsumerState<RegisterMatchScreen> {
  final _formKey = GlobalKey<FormState>();
  Game? _selectedGame;
  final Set<int> _selectedParticipants = {};
  int? _winnerId;
  final _durationController = TextEditingController();
  final _notesController = TextEditingController();
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    // Añadirse a uno mismo por defecto como participante
    final currentUser = ref.read(authProvider).user;
    if (currentUser != null) {
      _selectedParticipants.add(currentUser.id);
    }
  }

  @override
  void dispose() {
    _durationController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_selectedGame == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, selecciona un juego')),
      );
      return;
    }

    if (_selectedParticipants.length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Debes seleccionar al menos 2 participantes')),
      );
      return;
    }

    if (_winnerId == null || !_selectedParticipants.contains(_winnerId)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Debes elegir un ganador entre los participantes')),
      );
      return;
    }

    setState(() => _submitting = true);

    try {
      final duration = int.tryParse(_durationController.text.trim());
      final payload = MatchCreate(
        gameId: _selectedGame!.id,
        winnerId: _winnerId!,
        participantIds: _selectedParticipants.toList(),
        durationMinutes: duration,
        notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
      );

      await ref.read(matchRepositoryProvider).createMatch(widget.groupId, payload);
      ref.invalidate(groupMatchesProvider(widget.groupId));

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Partida registrada en estado PENDIENTE')),
        );
        context.pop();
      }
    } catch (e) {
      setState(() => _submitting = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error registrando partida: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final gamesAsync = ref.watch(groupGamesProvider(widget.groupId));
    final membersAsync = ref.watch(groupMembersProvider(widget.groupId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Registrar Partida'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '1. Selecciona el juego',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              gamesAsync.when(
                data: (games) {
                  if (games.isEmpty) {
                    return Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceDark,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Text(
                        'No hay juegos en este grupo. El administrador debe añadir juegos antes.',
                        style: TextStyle(color: Colors.amber),
                      ),
                    );
                  }
                  return DropdownButtonFormField<Game>(
                    value: _selectedGame,
                    hint: const Text('Elige un juego'),
                    items: games.map((g) {
                      return DropdownMenuItem<Game>(
                        value: g,
                        child: Text('${g.name} (${g.playersSpan})'),
                      );
                    }).toList(),
                    onChanged: (val) => setState(() => _selectedGame = val),
                  );
                },
                loading: () => const LinearProgressIndicator(),
                error: (e, _) => Text('Error cargando juegos: $e'),
              ),
              const SizedBox(height: 24),
              const Text(
                '2. Participantes (mínimo 2)',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              membersAsync.when(
                data: (members) {
                  return Card(
                    child: ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: members.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final member = members[index];
                        final isSelected = _selectedParticipants.contains(member.userId);

                        return CheckboxListTile(
                          title: Text(member.displayName ?? member.username),
                          subtitle: Text('@${member.username}', style: const TextStyle(color: AppColors.textMuted)),
                          value: isSelected,
                          onChanged: (checked) {
                            setState(() {
                              if (checked == true) {
                                _selectedParticipants.add(member.userId);
                              } else {
                                _selectedParticipants.remove(member.userId);
                                if (_winnerId == member.userId) {
                                  _winnerId = null;
                                }
                              }
                            });
                          },
                        );
                      },
                    ),
                  );
                },
                loading: () => const LinearProgressIndicator(),
                error: (e, _) => Text('Error cargando miembros: $e'),
              ),
              const SizedBox(height: 24),
              const Text(
                '3. Ganador de la partida',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              membersAsync.when(
                data: (members) {
                  final activeParticipants =
                      members.where((m) => _selectedParticipants.contains(m.userId)).toList();

                  if (activeParticipants.isEmpty) {
                    return const Text(
                      'Selecciona primero a los participantes arriba.',
                      style: TextStyle(color: AppColors.textMuted),
                    );
                  }

                  return DropdownButtonFormField<int>(
                    value: _winnerId,
                    hint: const Text('Elige al ganador'),
                    items: activeParticipants.map((m) {
                      return DropdownMenuItem<int>(
                        value: m.userId,
                        child: Text(m.displayName ?? m.username),
                      );
                    }).toList(),
                    onChanged: (val) => setState(() => _winnerId = val),
                  );
                },
                loading: () => const SizedBox(),
                error: (_, __) => const SizedBox(),
              ),
              const SizedBox(height: 24),
              const Text(
                '4. Detalles opcionales',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _durationController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Duración en minutos (opcional)',
                  prefixIcon: Icon(Icons.timer_outlined),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _notesController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Notas o comentarios de la partida (opcional)',
                  prefixIcon: Icon(Icons.notes_outlined),
                ),
              ),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _submitting ? null : _submit,
                  icon: const Icon(Icons.check_circle_outline),
                  label: _submitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Registrar Partida'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
