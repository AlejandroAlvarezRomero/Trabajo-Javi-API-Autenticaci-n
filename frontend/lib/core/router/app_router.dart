import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/achievements/screens/achievements_screen.dart';
import '../../features/auth/providers/auth_provider.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import '../../features/groups/screens/group_detail_screen.dart';
import '../../features/groups/screens/groups_list_screen.dart';
import '../../features/matches/screens/match_detail_screen.dart';
import '../../features/matches/screens/register_match_screen.dart';
import '../../features/notifications/screens/notifications_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../shared/widgets/app_scaffold.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorGroups = GlobalKey<NavigatorState>(debugLabel: 'groups');
final _shellNavigatorNotifications = GlobalKey<NavigatorState>(debugLabel: 'notifications');
final _shellNavigatorAchievements = GlobalKey<NavigatorState>(debugLabel: 'achievements');
final _shellNavigatorProfile = GlobalKey<NavigatorState>(debugLabel: 'profile');

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/groups',
    redirect: (context, state) {
      final isAuth = authState.isAuthenticated;
      final isLoggingIn = state.matchedLocation == '/login';
      final isRegistering = state.matchedLocation == '/register';

      // Si aún está en comprobación inicial, no redirigir todavía
      if (authState.status == AuthStatus.initial) {
        return null;
      }

      if (!isAuth && !isLoggingIn && !isRegistering) {
        return '/login';
      }

      if (isAuth && (isLoggingIn || isRegistering)) {
        return '/groups';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return AppScaffold(navigationShell: navigationShell);
        },
        branches: [
          // 0: Grupos
          StatefulShellBranch(
            navigatorKey: _shellNavigatorGroups,
            routes: [
              GoRoute(
                path: '/groups',
                builder: (context, state) => const GroupsListScreen(),
                routes: [
                  GoRoute(
                    path: ':id',
                    builder: (context, state) {
                      final id = int.parse(state.pathParameters['id']!);
                      return GroupDetailScreen(groupId: id);
                    },
                    routes: [
                      GoRoute(
                        path: 'matches/new',
                        parentNavigatorKey: _rootNavigatorKey,
                        builder: (context, state) {
                          final id = int.parse(state.pathParameters['id']!);
                          return RegisterMatchScreen(groupId: id);
                        },
                      ),
                      GoRoute(
                        path: 'matches/:matchId',
                        parentNavigatorKey: _rootNavigatorKey,
                        builder: (context, state) {
                          final id = int.parse(state.pathParameters['id']!);
                          final matchId = int.parse(state.pathParameters['matchId']!);
                          return MatchDetailScreen(groupId: id, matchId: matchId);
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
          // 1: Notificaciones
          StatefulShellBranch(
            navigatorKey: _shellNavigatorNotifications,
            routes: [
              GoRoute(
                path: '/notifications',
                builder: (context, state) => const NotificationsScreen(),
              ),
            ],
          ),
          // 2: Logros
          StatefulShellBranch(
            navigatorKey: _shellNavigatorAchievements,
            routes: [
              GoRoute(
                path: '/achievements',
                builder: (context, state) => const AchievementsScreen(),
              ),
            ],
          ),
          // 3: Perfil
          StatefulShellBranch(
            navigatorKey: _shellNavigatorProfile,
            routes: [
              GoRoute(
                path: '/profile',
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});
