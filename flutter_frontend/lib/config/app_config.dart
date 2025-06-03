import 'package:flutter_dotenv/flutter_dotenv.dart';

class AppConfig {
  /// Load .env file
  static Future<void> init() async {
    await dotenv.load(fileName: ".env");
  }

  /// Get base URLs from .env (supports multiple + fallback)
  static List<String> get baseUrls {
    final raw = dotenv.env['BASE_URLS'] ?? '';

    return raw
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .map(_normalizeUrl)
        .toList();
  }

  /// Primary API Base URL
  static String get defaultBaseUrl {
    final urls = baseUrls;
    if (urls.isEmpty) return 'API_NOT_CONFIGURED';
    return urls.first;
  }

  /// Fallback URLs (if primary fails)
  static List<String> get fallbackBaseUrls {
    final urls = baseUrls;
    if (urls.length <= 1) return [];
    return urls.sublist(1);
  }

  /// Optional credentials
  static String? get apiKey => dotenv.env['API_KEY'];
  static String? get apiSecret => dotenv.env['API_SECRET'];

  /// Environment (DEV / PROD / LOCAL)
  static String get environment =>
      dotenv.env['ENVIRONMENT']?.toUpperCase() ?? 'DEV';

  /// Normalize URL (remove trailing slash)
  static String _normalizeUrl(String url) {
    if (url.endsWith('/')) {
      return url.substring(0, url.length - 1);
    }
    return url;
  }
}
