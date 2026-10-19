import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/token_storage.dart';
import '../../../shared/models/user.dart';
import '../data/auth_repository.dart';

enum AuthStatus { initial, loading, authenticated, unauthenticated }

class AuthState {
  final AuthStatus status;
  final User? user;
  final String? errorMessage;

  const AuthState({
    this.status = AuthStatus.initial,
    this.user,
    this.errorMessage,
  });

  bool get isAuthenticated => status == AuthStatus.authenticated && user != null;

  AuthState copyWith({
    AuthStatus? status,
    User? user,
    String? errorMessage,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      errorMessage: errorMessage,
    );
  }
}

class AuthNotifier extends Notifier<AuthState> {
  late final AuthRepository _repo;

  @override
  AuthState build() {
    _repo = ref.watch(authRepositoryProvider);
    ApiClient().onSessionExpired = () {
      state = const AuthState(status: AuthStatus.unauthenticated);
    };
    // Comprobar token inicial en background
    Future.microtask(() => checkAuth());
    return const AuthState(status: AuthStatus.initial);
  }

  Future<void> checkAuth() async {
    final token = await TokenStorage.getAccessToken();
    if (token == null || token.isEmpty) {
      state = const AuthState(status: AuthStatus.unauthenticated);
      return;
    }

    try {
      final user = await _repo.getMe();
      state = AuthState(status: AuthStatus.authenticated, user: user);
    } catch (_) {
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  String _formatError(DioException e, String fallback) {
    if (e.response == null) {
      return 'No se pudo conectar con el servidor (http://localhost:8000). Comprueba que uvicorn esté corriendo.';
    }
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) {
      final detail = data['detail'];
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map && first['msg'] != null) {
          final field = first['loc'] is List && (first['loc'] as List).isNotEmpty
              ? (first['loc'] as List).last
              : '';
          return '${field.isNotEmpty ? "$field: " : ""}${first['msg']}';
        }
      }
    }
    return fallback;
  }

  Future<bool> login(String email, String password) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);
    try {
      await _repo.login(email: email, password: password);
      final user = await _repo.getMe();
      state = AuthState(status: AuthStatus.authenticated, user: user);
      return true;
    } on DioException catch (e) {
      state = AuthState(status: AuthStatus.unauthenticated, errorMessage: _formatError(e, 'Credenciales incorrectas'));
      return false;
    } catch (e) {
      state = AuthState(status: AuthStatus.unauthenticated, errorMessage: 'Error al iniciar sesión: $e');
      return false;
    }
  }

  Future<bool> register(String email, String username, String password) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);
    try {
      await _repo.register(email: email, username: username, password: password);
      // Auto login tras registro exitoso
      return await login(email, password);
    } on DioException catch (e) {
      state = AuthState(status: AuthStatus.unauthenticated, errorMessage: _formatError(e, 'Error al registrarse'));
      return false;
    } catch (e) {
      state = AuthState(status: AuthStatus.unauthenticated, errorMessage: 'Error de red: $e');
      return false;
    }
  }

  Future<bool> updateProfile({String? displayName, String? avatarUrl}) async {
    try {
      final updated = await _repo.updateProfile(displayName: displayName, avatarUrl: avatarUrl);
      state = state.copyWith(user: updated);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> uploadAvatar(List<int> bytes, String filename) async {
    try {
      final updated = await _repo.uploadAvatar(bytes, filename);
      state = state.copyWith(user: updated);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() async {
    await _repo.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}


final authRepositoryProvider = Provider((ref) => AuthRepository());

final authProvider = NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
