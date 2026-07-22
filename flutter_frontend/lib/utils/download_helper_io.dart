import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import 'error_handler.dart';

/// Downloads a file from the server in native (IO) environment
/// 
/// Saves the file to the system's Downloads directory or Documents
/// directory as a fallback.
/// 
/// Parameters:
/// - [filename]: The name of the file to download
/// - [baseUrl]: The base URL of the API server
/// 
/// Throws an exception if the download fails
Future<void> downloadFile(String filename, String baseUrl) async {
  final url = '$baseUrl/api/v1/download/$filename';
  
  ErrorHandler.logInfo('Starting IO download: $filename from $baseUrl');
  
  try {
    final response = await http.get(Uri.parse(url));

    if (response.statusCode == 200) {
      // Try downloads directory first, fallback to documents
      final dir = await getDownloadsDirectory() ?? 
                  await getApplicationDocumentsDirectory();
      
      // Sanitize filename to prevent path traversal
      final safeFilename = _sanitizeFilename(filename);
      final filePath = '${dir.path}/$safeFilename';
      
      // Ensure directory exists
      await dir.create(recursive: true);
      
      final file = File(filePath);
      await file.writeAsBytes(response.bodyBytes, flush: true);
      
      ErrorHandler.logInfo('IO download completed: $filePath (${response.bodyBytes.length} bytes)');
    } else if (response.statusCode == 404) {
      throw Exception('File not found: $filename');
    } else if (response.statusCode == 403) {
      throw Exception('Access denied: $filename');
    } else {
      throw Exception('Failed to download $filename (Status: ${response.statusCode})');
    }
  } on FileSystemException catch (e) {
    ErrorHandler.logError('File system error during download', error: e);
    throw Exception('Failed to save file: ${e.message}');
  } catch (e) {
    ErrorHandler.logError('IO download failed for $filename', error: e);
    rethrow;
  }
}

/// Sanitizes a filename to prevent path traversal attacks
/// 
/// Removes any path separators and potentially dangerous characters.
String _sanitizeFilename(String filename) {
  // Remove path separators
  String sanitized = filename.replaceAll('/', '_').replaceAll('\\', '_');
  
  // Remove null bytes
  sanitized = sanitized.replaceAll('\x00', '');
  
  // Remove parent directory references
  sanitized = sanitized.replaceAll('..', '_');
  
  // Trim whitespace
  sanitized = sanitized.trim();
  
  // If empty after sanitization, use a default name
  if (sanitized.isEmpty) {
    sanitized = 'download';
  }
  
  return sanitized;
}

/// Downloads a file to a specific directory
/// 
/// Parameters:
/// - [filename]: The name of the file to download
/// - [baseUrl]: The base URL of the API server
/// - [destinationDir]: The directory to save the file to
/// 
/// Returns the full path of the saved file
Future<String> downloadFileToDirectory(
  String filename,
  String baseUrl,
  String destinationDir,
) async {
  final url = '$baseUrl/api/v1/download/$filename';
  
  ErrorHandler.logInfo('Downloading to directory: $filename to $destinationDir');
  
  try {
    final response = await http.get(Uri.parse(url));

    if (response.statusCode == 200) {
      final safeFilename = _sanitizeFilename(filename);
      final filePath = '$destinationDir/$safeFilename';
      
      // Ensure directory exists
      final dir = Directory(destinationDir);
      await dir.create(recursive: true);
      
      final file = File(filePath);
      await file.writeAsBytes(response.bodyBytes, flush: true);
      
      ErrorHandler.logInfo('Download completed: $filePath');
      return filePath;
    } else if (response.statusCode == 404) {
      throw Exception('File not found: $filename');
    } else {
      throw Exception('Failed to download $filename (Status: ${response.statusCode})');
    }
  } catch (e) {
    ErrorHandler.logError('Download to directory failed', error: e);
    rethrow;
  }
}

/// Downloads multiple files to a specific directory
/// 
/// Returns a map of filenames to their saved paths or error messages
Future<Map<String, String>> downloadMultipleFilesToDirectory(
  List<String> filenames,
  String baseUrl,
  String destinationDir,
) async {
  final results = <String, String>{};
  
  for (final filename in filenames) {
    try {
      final path = await downloadFileToDirectory(filename, baseUrl, destinationDir);
      results[filename] = path;
    } catch (e) {
      results[filename] = 'Error: $e';
    }
  }
  
  return results;
}
