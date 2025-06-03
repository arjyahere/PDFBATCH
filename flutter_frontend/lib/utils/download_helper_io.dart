import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

Future<void> downloadFile(String filename, String baseUrl) async {
  final url = '$baseUrl/download/$filename';
  final response = await http.get(Uri.parse(url));

  if (response.statusCode == 200) {
    final dir = await getDownloadsDirectory() ?? await getApplicationDocumentsDirectory();
    final filePath = '${dir.path}/$filename';
    final file = File(filePath);
    await file.writeAsBytes(response.bodyBytes, flush: true);
  } else {
    throw Exception("Failed to download $filename");
  }
}
