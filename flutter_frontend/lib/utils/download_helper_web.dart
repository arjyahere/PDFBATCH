// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'package:http/http.dart' as http;

Future<void> downloadFile(String filename, String baseUrl) async {
  final url = '$baseUrl/download/$filename';
  final response = await http.get(Uri.parse(url));

  if (response.statusCode == 200) {
    final blob = html.Blob([response.bodyBytes]);
    final blobUrl = html.Url.createObjectUrlFromBlob(blob);
    final _ = html.AnchorElement(href: blobUrl)
      ..setAttribute('download', filename)
      ..click();
    html.Url.revokeObjectUrl(blobUrl);
  } else {
    throw Exception("Failed to download $filename");
  }
}
