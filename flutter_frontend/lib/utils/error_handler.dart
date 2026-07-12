import 'dart:convert';
import 'dart:developer' as developer;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Comprehensive error handler for the application
/// 
/// Provides user-friendly error messages, logging, and UI components
/// for displaying errors throughout the app.
class ErrorHandler {
  ErrorHandler._();

  /// Log an error with optional stack trace
  /// 
  /// In debug mode, prints to console. In production, uses developer.log.
  static void logError(String message, {Object? error, StackTrace? stackTrace, String? tag}) {
    final logTag = tag ?? 'BatchHighlighter';
    final fullMessage = error != null ? '$message: $error' : message;
    
    if (kDebugMode) {
      debugPrint('[$logTag] ERROR: $fullMessage');
      if (stackTrace != null) {
        debugPrint('[$logTag] StackTrace: $stackTrace');
      }
    } else {
      developer.log(
        fullMessage,
        name: logTag,
        error: error,
        stackTrace: stackTrace,
      );
    }
  }

  /// Log an info message
  static void logInfo(String message, {String? tag}) {
    final logTag = tag ?? 'BatchHighlighter';
    
    if (kDebugMode) {
      debugPrint('[$logTag] INFO: $message');
    } else {
      developer.log(message, name: logTag);
    }
  }

  /// Show an error snackbar with optional retry action
  /// 
  /// Displays a user-friendly error message at the bottom of the screen.
  /// If [retryAction] is provided, shows a retry button.
  static void showErrorSnackBar(
    BuildContext context,
    String error, {
    VoidCallback? retryAction,
    Duration duration = const Duration(seconds: 5),
  }) {
    logError('Showing error to user: $error');
    
    final snackBar = SnackBar(
      content: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.white),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _getUserFriendlyMessage(error),
              style: const TextStyle(color: Colors.white),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
      backgroundColor: Colors.red.shade700,
      duration: duration,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      action: retryAction != null
          ? SnackBarAction(
              label: 'Retry',
              textColor: Colors.white,
              onPressed: () {
                ScaffoldMessenger.of(context).hideCurrentSnackBar();
                retryAction();
              },
            )
          : null,
    );

    ScaffoldMessenger.of(context).showSnackBar(snackBar);
  }

  /// Show a success snackbar
  static void showSuccessSnackBar(
    BuildContext context,
    String message, {
    Duration duration = const Duration(seconds: 3),
  }) {
    final snackBar = SnackBar(
      content: Row(
        children: [
          const Icon(Icons.check_circle_outline, color: Colors.white),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      backgroundColor: Colors.green.shade700,
      duration: duration,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    );

    ScaffoldMessenger.of(context).showSnackBar(snackBar);
  }

  /// Show an info snackbar
  static void showInfoSnackBar(
    BuildContext context,
    String message, {
    Duration duration = const Duration(seconds: 3),
  }) {
    final snackBar = SnackBar(
      content: Row(
        children: [
          const Icon(Icons.info_outline, color: Colors.white),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      backgroundColor: Colors.blue.shade700,
      duration: duration,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    );

    ScaffoldMessenger.of(context).showSnackBar(snackBar);
  }

  /// Show a warning snackbar
  static void showWarningSnackBar(
    BuildContext context,
    String message, {
    Duration duration = const Duration(seconds: 4),
  }) {
    final snackBar = SnackBar(
      content: Row(
        children: [
          const Icon(Icons.warning_amber_outlined, color: Colors.white),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      backgroundColor: Colors.orange.shade700,
      duration: duration,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    );

    ScaffoldMessenger.of(context).showSnackBar(snackBar);
  }

  /// Convert technical error messages to user-friendly ones
  static String _getUserFriendlyMessage(String error) {
    final lowerError = error.toLowerCase();

    // Try to parse as JSON for structured errors
    try {
      final errorMap = json.decode(error);
      if (errorMap is Map<String, dynamic>) {
        if (errorMap.containsKey('message')) {
          return errorMap['message'].toString();
        }
        if (errorMap.containsKey('error')) {
          final innerError = errorMap['error'];
          if (innerError is Map && innerError.containsKey('message')) {
            return innerError['message'].toString();
          }
          return innerError.toString();
        }
      }
    } catch (_) {
      // Not JSON, continue with string matching
    }

    // Network errors
    if (lowerError.contains('socket') || 
        lowerError.contains('network') || 
        lowerError.contains('connection') ||
        lowerError.contains('failed host lookup')) {
      return 'Unable to connect to the server. Please check your internet connection and try again.';
    }

    if (lowerError.contains('timeout')) {
      return 'The request timed out. The server might be busy. Please try again.';
    }

    // Server errors
    if (lowerError.contains('server') && lowerError.contains('unreachable')) {
      return 'Server is currently unreachable. Please try again later.';
    }

    if (lowerError.contains('404') || lowerError.contains('not found')) {
      return 'The requested resource was not found. Please check your configuration.';
    }

    if (lowerError.contains('500') || lowerError.contains('internal server error')) {
      return 'A server error occurred. Please try again later.';
    }

    if (lowerError.contains('503') || lowerError.contains('service unavailable')) {
      return 'The service is temporarily unavailable. Please try again later.';
    }

    // File errors
    if (lowerError.contains('file') && lowerError.contains('not found')) {
      return 'File not found. Please check if the file exists and try again.';
    }

    if (lowerError.contains('permission') || lowerError.contains('access denied')) {
      return 'Permission denied. Please check file permissions and try again.';
    }

    if (lowerError.contains('invalid') && lowerError.contains('file')) {
      return 'Invalid file format. Please select a supported file type.';
    }

    if (lowerError.contains('file too large') || lowerError.contains('entity too large')) {
      return 'The file is too large. Please select a smaller file.';
    }

    // Processing errors
    if (lowerError.contains('processing') && lowerError.contains('failed')) {
      return 'Processing failed. Please check your files and try again.';
    }

    if (lowerError.contains('already in progress')) {
      return 'A process is already running. Please wait for it to complete.';
    }

    // Validation errors
    if (lowerError.contains('missing') || lowerError.contains('required')) {
      return 'Please fill in all required fields before proceeding.';
    }

    if (lowerError.contains('invalid') || lowerError.contains('bad request')) {
      return 'Invalid input. Please check your entries and try again.';
    }

    // Authentication errors
    if (lowerError.contains('unauthorized') || lowerError.contains('401')) {
      return 'You are not authorized to perform this action. Please check your credentials.';
    }

    if (lowerError.contains('forbidden') || lowerError.contains('403')) {
      return 'Access forbidden. You don\'t have permission to perform this action.';
    }

    // Default fallback
    if (kDebugMode) {
      return 'Error: $error';
    }
    return 'An unexpected error occurred. Please try again.';
  }

  /// Build a full-screen error widget
  static Widget buildErrorWidget({
    required String error,
    required VoidCallback onRetry,
    String? title,
    IconData? icon,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon ?? Icons.error_outline,
              size: 64,
              color: Colors.red.shade300,
            ),
            const SizedBox(height: 16),
            Text(
              title ?? 'Something went wrong',
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              _getUserFriendlyMessage(error),
              style: TextStyle(
                fontSize: 16,
                color: Colors.grey.shade600,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build an empty state widget
  static Widget buildEmptyState({
    required String message,
    String? subtitle,
    IconData icon = Icons.inbox,
    VoidCallback? onAction,
    String? actionLabel,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 64,
              color: Colors.grey.shade400,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w500,
                color: Colors.grey.shade600,
              ),
              textAlign: TextAlign.center,
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey.shade500,
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (onAction != null && actionLabel != null) ...[
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: onAction,
                icon: const Icon(Icons.add),
                label: Text(actionLabel),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Handle async errors with proper logging
  static Future<T?> handleAsync<T>(
    Future<T> Function() operation, {
    String? operationName,
    void Function(Object error, StackTrace)? onError,
  }) async {
    try {
      return await operation();
    } catch (error, stackTrace) {
      logError(
        operationName ?? 'Async operation failed',
        error: error,
        stackTrace: stackTrace,
      );
      onError?.call(error, stackTrace);
      return null;
    }
  }
}
