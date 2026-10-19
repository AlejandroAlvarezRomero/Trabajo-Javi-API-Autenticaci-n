import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../shared/models/group.dart';
import '../data/group_repository.dart';

final groupRepositoryProvider = Provider((ref) => GroupRepository());

// Proveedor de la lista de grupos del usuario actual
final myGroupsProvider =
    AsyncNotifierProvider<MyGroupsNotifier, List<Group>>(MyGroupsNotifier.new);

class MyGroupsNotifier extends AsyncNotifier<List<Group>> {
  @override
  Future<List<Group>> build() async {
    final repo = ref.watch(groupRepositoryProvider);
    return repo.getMyGroups();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() => ref.read(groupRepositoryProvider).getMyGroups());
  }

  Future<Group> createGroup(String name, String? description) async {
    final newGroup = await ref.read(groupRepositoryProvider).createGroup(name, description);
    await refresh();
    return newGroup;
  }

  Future<Group> joinGroup(String inviteCode) async {
    final joined = await ref.read(groupRepositoryProvider).joinGroup(inviteCode);
    await refresh();
    return joined;
  }

  Future<void> leaveGroup(int groupId) async {
    await ref.read(groupRepositoryProvider).leaveGroup(groupId);
    await refresh();
  }

  Future<void> deleteGroup(int groupId) async {
    await ref.read(groupRepositoryProvider).deleteGroup(groupId);
    await refresh();
  }
}

// Proveedor de detalle de un grupo específico
final groupDetailProvider =
    FutureProvider.family<Group, int>((ref, groupId) async {
  final repo = ref.watch(groupRepositoryProvider);
  return repo.getGroup(groupId);
});

// Proveedor de miembros de un grupo
final groupMembersProvider =
    FutureProvider.family<List<Member>, int>((ref, groupId) async {
  final repo = ref.watch(groupRepositoryProvider);
  return repo.getMembers(groupId);
});
