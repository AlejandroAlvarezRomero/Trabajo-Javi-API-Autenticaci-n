import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/games_provider.dart';

class BggSearchDialog extends ConsumerStatefulWidget {
  final int groupId;

  const BggSearchDialog({super.key, required this.groupId});

  @override
  ConsumerState<BggSearchDialog> createState() => _BggSearchDialogState();
}

class _BggSearchDialogState extends ConsumerState<BggSearchDialog> {
  final _searchController = TextEditingController();
  bool _searching = false;
  bool _adding = false;
  List<dynamic> _results = [];
  String? _errorMessage;

  Future<void> _performSearch() async {
    final query = _searchController.text.trim();
    if (query.isEmpty) return;

    setState(() {
      _searching = true;
      _errorMessage = null;
    });

    try {
      final repo = ref.read(gameRepositoryProvider);
      final results = await repo.searchBgg(widget.groupId, query);
      setState(() {
        _results = results;
        _searching = false;
        if (results.isEmpty) {
          _errorMessage = 'No se encontraron juegos con "$query".';
        }
      });
    } catch (e) {
      setState(() {
        if (e is DioException && e.response?.data is Map && e.response?.data['detail'] != null) {
          _errorMessage = e.response!.data['detail'].toString();
        } else {
          _errorMessage = 'No se pudo contactar con el buscador. Inténtalo de nuevo.';
        }
        _searching = false;
      });
    }
  }

  Future<void> _addGame(int bggId, String name) async {
    setState(() => _adding = true);
    try {
      await ref.read(gameRepositoryProvider).addGameFromBgg(widget.groupId, bggId);
      ref.invalidate(groupGamesProvider(widget.groupId));
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Juego "$name" añadido al catálogo')),
        );
      }
    } catch (e) {
      setState(() => _adding = false);
      String msg = 'Error añadiendo juego';
      if (e is DioException && e.response?.data is Map && e.response?.data['detail'] != null) {
        msg = e.response!.data['detail'].toString();
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg)),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 550, maxHeight: 600),
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Buscar en BoardGameGeek',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _searchController,
                      decoration: const InputDecoration(
                        hintText: 'Ej. Catan, Terraforming Mars...',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onSubmitted: (_) => _performSearch(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _searching ? null : _performSearch,
                    child: _searching
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Buscar'),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (_errorMessage != null)
                Text(_errorMessage!, style: const TextStyle(color: Colors.redAccent)),
              if (_adding)
                const LinearProgressIndicator(),
              Expanded(
                child: _results.isEmpty && !_searching
                    ? const Center(
                        child: Text(
                          'Escribe el nombre de un juego para buscar en BGG',
                          style: TextStyle(color: AppColors.textMuted),
                        ),
                      )
                    : ListView.separated(
                        itemCount: _results.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final item = _results[index];
                          return ListTile(
                            title: Text(item.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                            subtitle: item.yearPublished != null
                                ? Text('Año: ${item.yearPublished}', style: const TextStyle(color: AppColors.textMuted))
                                : null,
                            trailing: ElevatedButton.icon(
                              icon: const Icon(Icons.add, size: 16),
                              label: const Text('Añadir'),
                              onPressed: _adding ? null : () => _addGame(item.bggId, item.name),
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
