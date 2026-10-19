class ApiEndpoints {
  // Base URL configurable
  static const String baseUrl = 'http://localhost:8000/api/v1';

  // Auth
  static const String register = '/auth/register';
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String logout = '/auth/logout';
  static const String me = '/auth/me';
  static const String avatar = '/auth/avatar';
  static const String forgotPassword = '/auth/forgot-password';
  static const String resetPassword = '/auth/reset-password';


  // Groups
  static const String groups = '/groups';
  static const String joinGroup = '/groups/join';
  static String groupDetail(int groupId) => '/groups/$groupId';
  static String groupMembers(int groupId) => '/groups/$groupId/members';
  static String groupMember(int groupId, int userId) => '/groups/$groupId/members/$userId';
  static String leaveGroup(int groupId) => '/groups/$groupId/leave';
  static String transferOwnership(int groupId) => '/groups/$groupId/transfer-ownership';

  // Games
  static String groupGames(int groupId) => '/groups/$groupId/games';
  static String groupGame(int groupId, int gameId) => '/groups/$groupId/games/$gameId';
  static String searchBgg(int groupId) => '/groups/$groupId/games/search';
  static String seedPopularGames(int groupId) => '/groups/$groupId/games/seed-popular';

  // Matches
  static String groupMatches(int groupId) => '/groups/$groupId/matches';
  static String groupMatch(int groupId, int matchId) => '/groups/$groupId/matches/$matchId';
  static String confirmMatch(int groupId, int matchId) => '/groups/$groupId/matches/$matchId/confirm';
  static String rejectMatch(int groupId, int matchId) => '/groups/$groupId/matches/$matchId/reject';
  static String cancelMatch(int groupId, int matchId) => '/groups/$groupId/matches/$matchId/cancel';

  // Seasons
  static String groupSeasons(int groupId) => '/groups/$groupId/seasons';
  static String seasonRollover(int groupId) => '/groups/$groupId/seasons/rollover';

  // Stats
  static String leaderboard(int groupId) => '/groups/$groupId/leaderboard';
  static String myStats(int groupId) => '/groups/$groupId/stats/me';
  static String userStats(int groupId, int userId) => '/groups/$groupId/stats/users/$userId';

  // Notifications
  static const String notifications = '/notifications';
  static const String notificationStream = '/notifications/stream';
  static String markNotificationRead(int id) => '/notifications/$id/read';
  static const String markAllNotificationsRead = '/notifications/read-all';

  // Achievements
  static const String achievements = '/achievements';
  static const String myAchievements = '/users/me/achievements';

  // Helper para resolver URLs relativas (como /uploads/avatars/...)
  static String resolveUrl(String? path) {
    if (path == null || path.isEmpty) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    const serverHost = 'http://localhost:8000';
    return path.startsWith('/') ? '$serverHost$path' : '$serverHost/$path';
  }
}

