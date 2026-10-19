import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../storage/token_storage.dart';
import 'api_endpoints.dart';

class AuthInterceptor extends Interceptor {
  final Dio dio;
  final VoidCallback? onSessionExpired;
  bool _isRefreshing = false;

  AuthInterceptor({required this.dio, this.onSessionExpired});

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Si la ruta no es login ni register, añadir Bearer token
    if (!options.path.contains('/auth/login') &&
        !options.path.contains('/auth/register') &&
        !options.path.contains('/auth/refresh')) {
      final token = await TokenStorage.getAccessToken();
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    }
    return handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401) {
      final requestPath = err.requestOptions.path;
      // No intentar refrescar si el 401 vino del login o del mismo refresh
      if (requestPath.contains('/auth/login') ||
          requestPath.contains('/auth/refresh')) {
        return handler.next(err);
      }

      if (!_isRefreshing) {
        _isRefreshing = true;
        try {
          // Intentar refresh silencioso
          final refreshDio = Dio(
            BaseOptions(
              baseUrl: dio.options.baseUrl,
              extra: {'withCredentials': true},
              headers: {'Content-Type': 'application/json'},
            ),
          );

          final response = await refreshDio.post(ApiEndpoints.refresh);
          final newAccessToken = response.data['access_token'] as String?;

          if (newAccessToken != null) {
            await TokenStorage.saveAccessToken(newAccessToken);
            _isRefreshing = false;

            // Reintentar la petición original con el nuevo token
            final options = err.requestOptions;
            options.headers['Authorization'] = 'Bearer $newAccessToken';

            final retryResponse = await dio.fetch(options);
            return handler.resolve(retryResponse);
          }
        } catch (e) {
          _isRefreshing = false;
          await TokenStorage.clear();
          onSessionExpired?.call();
        }
      }
    }

    return handler.next(err);
  }
}
