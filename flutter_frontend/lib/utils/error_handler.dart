import 'package:flutter/material.dart';

class ErrorHandler {
  static void showErrorSnackBar(BuildContext context, String error, {VoidCallback? retryAction}) {
    final snackBar = SnackBar(
      content: Row(
        children: [
          const Icon(Icons.error, color: Colors.white),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _getUserFriendlyMessage(error),
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      backgroundColor: Colors.red,
      duration: const Duration(seconds: 5),
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

  static void showSuccessSnackBar(BuildContext context, String message) {
    final snackBar = SnackBar(
      content: Row(
        children: [
          const Icon(Icons.check_circle, color: Colors.white),
          const SizedBox(width: 8),
          Expanded(
            child: Text(message, style: const TextStyle(color: Colors.white)),
          ),
        ],
      ),
      backgroundColor: Colors.green,
      duration: const Duration(seconds: 3),
    );

    ScaffoldMessenger.of(context).showSnackBar(snackBar);
  }

  static void showInfoSnackBar(BuildContext context, String message) {
    final snackBar = SnackBar(
      content: Row(
        children: [
          const Icon(Icons.info, color: Colors.white),
          const SizedBox(width: 8),
          Expanded(
            child: Text(message, style: const TextStyle(color: Colors.white)),
          ),
        ],
      ),
      backgroundColor: Colors.blue,
      duration: const Duration(seconds: 3),
    );

    ScaffoldMessenger.of(context).showSnackBar(snackBar);
  }

  static String _getUserFriendlyMessage(String error) {
    final lowerError = error.toLowerCase();

    if (lowerError.contains('network') || lowerError.contains('connection')) {
      return 'Network connection error. Please check your internet connection and try again.';
    }

    if (lowerError.contains('timeout')) {
      return 'Request timed out. The server might be busy. Please try again.';
    }

    if (lowerError.contains('file') && lowerError.contains('not found')) {
      return 'File not found. Please check if the file exists and try again.';
    }

    if (lowerError.contains('permission') || lowerError.contains('access denied')) {
      return 'Permission denied. Please check file permissions and try again.';
    }

    if (lowerError.contains('server') && lowerError.contains('unreachable')) {
      return 'Server is currently unreachable. Please try again later.';
    }

    if (lowerError.contains('invalid') && lowerError.contains('file')) {
      return 'Invalid file format. Please select a supported file type.';
    }

    if (lowerError.contains('processing') && lowerError.contains('failed')) {
      return 'Processing failed. Please check your files and try again.';
    }

    // Default fallback
    return 'An error occurred: $error';
  }

  static Widget buildErrorWidget({
    required String error,
    required VoidCallback onRetry,
    String? title,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
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
}