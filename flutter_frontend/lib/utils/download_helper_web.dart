import 'dart:js_interop';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

import 'error_handler.dart';

/// Downloads a file from the server in web environment
/// 
/// Uses the browser's download mechanism via anchor element.
/// The file is fetched from the server and then triggered as a download.
/// 
/// Parameters:
/// - [filename]: The name of the file to download
/// - [baseUrl]: The base URL of the API server
/// 
/// Throws an exception if the download fails
Future<void> downloadFile(String filename, String baseUrl) async {
  final url = '$baseUrl/api/v1/download/$filename';
  
  ErrorHandler.logInfo('Starting web download: $filename from $baseUrl');
  
  try {
    final response = await http.get(Uri.parse(url));

    if (response.statusCode == 200) {
      final bytes = response.bodyBytes;
      _triggerBrowserDownload(filename, bytes);
      ErrorHandler.logInfo('Web download completed: $filename (${bytes.length} bytes)');
    } else if (response.statusCode == 404) {
      throw Exception('File not found: $filename');
    } else if (response.statusCode == 403) {
      throw Exception('Access denied: $filename');
    } else {
      throw Exception('Failed to download $filename (Status: ${response.statusCode})');
    }
  } catch (e) {
    ErrorHandler.logError('Web download failed for $filename', error: e);
    rethrow;
  }
}

/// Triggers a browser download using an anchor element
/// 
/// Creates a blob URL from the bytes and simulates a click on a hidden
/// anchor element to trigger the download dialog.
void _triggerBrowserDownload(String filename, Uint8List bytes) {
  try {
    // Convert Uint8List to JS array
    final jsArray = bytes.toJS;
    
    // Create blob with the file content
    final blob = web.Blob([jsArray].toJS);
    
    // Create object URL
    final blobUrl = web.URL.createObjectURL(blob);
    
    // Create and configure anchor element
    final anchor = web.HTMLAnchorElement();
    anchor.href = blobUrl;
    anchor.setAttribute('download', filename);
    
    // Trigger download
    anchor.click();
    
    // Clean up
    web.URL.revokeObjectURL(blobUrl);
  } catch (e) {
    ErrorHandler.logError('Failed to trigger browser download', error: e);
    throw Exception('Failed to initiate download: $e');
  }
}

/// Downloads multiple files sequentially
/// 
/// Downloads each file one by one to avoid overwhelming the browser.
/// Returns a list of failed filenames.
Future<List<String>> downloadMultipleFiles(
  List<String> filenames,
  String baseUrl,
) async {
  final failed = <String>[];
  
  for (final filename in filenames) {
    try {
      await downloadFile(filename, baseUrl);
      // Small delay between downloads to prevent browser throttling
      await Future.delayed(const Duration(milliseconds: 100));
    } catch (e) {
      failed.add(filename);
      ErrorHandler.logError('Failed to download $filename', error: e);
    }
  }
  
  return failed;
}
