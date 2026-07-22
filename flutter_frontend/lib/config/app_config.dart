import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Application configuration class
/// 
/// Manages environment-specific settings loaded from .env file.
/// Provides centralized access to API URLs, credentials, and environment settings.
class AppConfig {
  AppConfig._();

  static bool _initialized = false;
  static final String _fallbackBaseUrl = 'http://127.0.0.1:8000';

  /// Initialize configuration
  /// 
  /// Loads the .env file. If loading fails in production,
  /// logs a warning but doesn't crash the app.
  static Future<void> init() async {
    if (_initialized) return;
    
    try {
      await dotenv.load(fileName: '.env');
      _initialized = true;
    } catch (e) {
      if (kReleaseMode) {
        debugPrint('Warning: Could not load .env file: $e');
      }
      // In production, we might want to use default values or show an error
      _initialized = false;
    }
  }

  /// Get base URLs from .env (supports multiple + fallback)
  /// 
  /// Parses comma-separated URLs and normalizes them.
  /// Returns fallback URL if no URLs are configured.
  static List<String> get baseUrls {
    final raw = dotenv.env['BASE_URLS'] ?? '';
    
    if (raw.isEmpty) {
      return [_fallbackBaseUrl];
    }

    final urls = raw
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .map(_normalizeUrl)
        .toList();
    
    return urls.isNotEmpty ? urls : [_fallbackBaseUrl];
  }

  /// Primary API Base URL
  /// 
  /// Returns the first configured URL or the fallback if none are available.
  static String get defaultBaseUrl {
    final urls = baseUrls;
    if (urls.isEmpty) return _fallbackBaseUrl;
    return urls.first;
  }

  /// Fallback URLs (if primary fails)
  /// 
  /// Returns all URLs except the primary one for failover support.
  static List<String> get fallbackBaseUrls {
    final urls = baseUrls;
    if (urls.length <= 1) return [];
    return urls.sublist(1);
  }

  /// API Version from environment
  static String get apiVersion => dotenv.env['API_VERSION'] ?? 'v1';

  /// Optional API credentials
  static String? get apiKey => dotenv.env['API_KEY'];
  static String? get apiSecret => dotenv.env['API_SECRET'];

  /// Environment identifier (DEV / PROD / STAGING)
  static String get environment {
    final env = dotenv.env['ENVIRONMENT']?.toUpperCase() ?? 'DEV';
    return ['DEV', 'PROD', 'STAGING', 'LOCAL'].contains(env) ? env : 'DEV';
  }

  /// Check if running in production mode
  static bool get isProduction => environment == 'PROD';

  /// Check if running in development mode
  static bool get isDevelopment => environment == 'DEV';

  /// Request timeout durations
  static Duration get defaultTimeout => const Duration(seconds: 30);
  static Duration get uploadTimeout => const Duration(seconds: 120);
  static Duration get downloadTimeout => const Duration(seconds: 60);

  /// Polling interval for progress updates
  static Duration get progressPollingInterval => const Duration(seconds: 10);

  /// Normalize URL (remove trailing slash)
  static String _normalizeUrl(String url) {
    url = url.trim();
    if (url.endsWith('/')) {
      return url.substring(0, url.length - 1);
    }
    return url;
  }

  /// Validate URL format
  static bool isValidUrl(String url) {
    try {
      final uri = Uri.parse(url);
      return uri.isAbsolute && (uri.scheme == 'http' || uri.scheme == 'https');
    } catch (_) {
      return false;
    }
  }
}
