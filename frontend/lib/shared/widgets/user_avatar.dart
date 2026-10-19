import 'package:flutter/material.dart';
import '../../core/network/api_endpoints.dart';
import '../../core/theme/app_theme.dart';

class UserAvatar extends StatelessWidget {
  final String? avatarUrl;
  final String name;
  final double radius;
  final VoidCallback? onTap;

  const UserAvatar({
    super.key,
    required this.avatarUrl,
    required this.name,
    this.radius = 20,
    this.onTap,
  });

  String get _initials {
    final clean = name.trim();
    if (clean.isEmpty) return '?';
    final parts = clean.split(' ').where((p) => p.isNotEmpty).toList();
    if (parts.length > 1) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return clean.substring(0, clean.length >= 2 ? 2 : 1).toUpperCase();
  }

  Color _generateColor(String text) {
    const colors = [
      AppColors.primary,
      Colors.indigoAccent,
      Colors.teal,
      Colors.purpleAccent,
      Colors.deepOrangeAccent,
      Colors.cyan,
      Colors.pinkAccent,
    ];
    final hash = text.hashCode.abs();
    return colors[hash % colors.length];
  }

  @override
  Widget build(BuildContext context) {
    final resolvedUrl = ApiEndpoints.resolveUrl(avatarUrl);
    final hasValidUrl = resolvedUrl.isNotEmpty;

    Widget avatar = CircleAvatar(
      radius: radius,
      backgroundColor: _generateColor(name).withValues(alpha: 0.25),
      child: hasValidUrl
          ? ClipOval(
              child: Image.network(
                resolvedUrl,
                width: radius * 2,
                height: radius * 2,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) {
                  return Center(
                    child: Text(
                      _initials,
                      style: TextStyle(
                        fontSize: radius * 0.8,
                        fontWeight: FontWeight.bold,
                        color: _generateColor(name),
                      ),
                    ),
                  );
                },
              ),
            )
          : Center(
              child: Text(
                _initials,
                style: TextStyle(
                  fontSize: radius * 0.8,
                  fontWeight: FontWeight.bold,
                  color: _generateColor(name),
                ),
              ),
            ),
    );

    if (onTap != null) {
      avatar = InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(radius),
        child: avatar,
      );
    }

    return avatar;
  }
}
