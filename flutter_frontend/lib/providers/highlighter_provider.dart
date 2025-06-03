import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import '../utils/download_helper.dart' as downloader;

class HighlighterProvider with ChangeNotifier {
  /// -------------------------------------------------------
  /// Server & HTTP
  /// -------------------------------------------------------
  String baseUrl = AppConfig.defaultBaseUrl;

  int _activeServerIndex = 0;
  List<String> get _servers => AppConfig.baseUrls;

  final http.Client _client;
  final bool _ownsClient;

  Timer? _pollTimer;
  bool _disposed = false;

  HighlighterProvider({http.Client? client})
      : _client = client ?? http.Client(),
        _ownsClient = client == null;

  // -------------------------------------------------------
  // Safe Request With Fallback
  // -------------------------------------------------------
  Future<T> _safeRequest<T>(Future<T> Function(String url) fn) async {
    final servers = _servers;

    for (int i = 0; i < servers.length; i++) {
      final index = (_activeServerIndex + i) % servers.length;
      final url = servers[index];

      try {
        final result = await fn(url);

        _activeServerIndex = index;
        baseUrl = url;

        return result;
      } catch (_) {
        continue;
      }
    }

    throw Exception('All API servers are unreachable');
  }

  // -------------------------------------------------------
  // Manual Server Switching
  // -------------------------------------------------------
  List<String> get availableServers => _servers;

  void setBaseUrl(String url) {
    final index = _servers.indexOf(url.trim());
    if (index != -1) {
      _activeServerIndex = index;
      baseUrl = _servers[index];
      notifyListeners();
    }
  }

  void setBaseUrlByIndex(int index) {
    if (index >= 0 && index < _servers.length) {
      _activeServerIndex = index;
      baseUrl = _servers[index];
      notifyListeners();
    }
  }

  // -------------------------------------------------------
  // State
  // -------------------------------------------------------
  PlatformFile? _dataFile;
  List<PlatformFile> _documentFiles = [];
  List<String> _columns = [];
  String? _selectedColumn;
  String _selectedColor = 'Yellow';
  bool _isLoadingColumns = false;
  String? _columnsError;

  bool _isProcessing = false;
  double _progress = 0.0;
  String _status = 'Idle';
  List<Map<String, dynamic>> _logs = [];
  String? _combinedLogFile;
  String? _unmatchedValuesFile;
  String? _destFolder;

  final List<String> colorOptions = [
    'Yellow',
    'Green',
    'Cyan',
    'Pink',
    'Blue',
    'Red',
  ];

  // -------------------------------------------------------
  // Getters
  // -------------------------------------------------------
  PlatformFile? get dataFile => _dataFile;
  List<PlatformFile> get documentFiles => List.unmodifiable(_documentFiles);
  List<String> get columns => List.unmodifiable(_columns);
  String? get selectedColumn => _selectedColumn;
  String get selectedColor => _selectedColor;
  bool get isLoadingColumns => _isLoadingColumns;
  String? get columnsError => _columnsError;

  bool get isProcessing => _isProcessing;
  double get progress => _progress;
  String get status => _status;
  List<Map<String, dynamic>> get logs => List.unmodifiable(_logs);
  String? get combinedLogFile => _combinedLogFile;
  String? get unmatchedValuesFile => _unmatchedValuesFile;
  String? get destFolder => _destFolder;

  // -------------------------------------------------------
  // Setters
  // -------------------------------------------------------
  void setDataFile(PlatformFile? file) {
    _dataFile = file;
    _columns.clear();
    _selectedColumn = null;
    _columnsError = null;
    notifyListeners();
  }

  void setDocumentFiles(List<PlatformFile> files) {
    _documentFiles = List.from(files);
    notifyListeners();
  }

  void setSelectedColumn(String? column) {
    _selectedColumn = column;
    notifyListeners();
  }

  void setSelectedColor(String color) {
    _selectedColor = color;
    notifyListeners();
  }
  

    // -------------------------------------------------------
  // Document File Management  ✅ FIXED
  // -------------------------------------------------------

  void addDocumentFile(PlatformFile file) {
    _documentFiles.add(file);
    notifyListeners();
  }

  void addMultipleDocumentFiles(List<PlatformFile> files) {
    _documentFiles.addAll(files);
    notifyListeners();
  }

  void removeDocumentFileAt(int index) {
    if (index >= 0 && index < _documentFiles.length) {
      _documentFiles.removeAt(index);
      notifyListeners();
    }
  }

  void clearDocumentFiles() {
    _documentFiles.clear();
    notifyListeners();
  }


  // -------------------------------------------------------
  // Generic File Download (FOR UI FIX)
  // -------------------------------------------------------
  Future<String?> downloadFile(String fileName) async {
    try {
      await downloader.downloadFile(fileName, baseUrl);
      return null;
    } catch (e) {
      return 'Download error: $e';
    }
  }


  // -------------------------------------------------------
  // Multipart Helper
  // -------------------------------------------------------
  Future<void> _addPlatformFileToRequest(
    http.MultipartRequest request,
    String fieldName,
    PlatformFile file, {
    String? filename,
  }) async {
    final fname = filename ?? file.name;

    if (file.bytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes(fieldName, file.bytes!, filename: fname),
      );
      return;
    }

    if (!kIsWeb && file.path != null) {
      request.files.add(
        await http.MultipartFile.fromPath(fieldName, file.path!, filename: fname),
      );
      return;
    }

    throw Exception('File "${file.name}" has no bytes and no path.');
  }

  // -------------------------------------------------------
  // Load Columns (with fallback)
  // -------------------------------------------------------
  Future<void> loadColumns({Duration timeout = const Duration(seconds: 30)}) async {
    if (_dataFile == null) return;

    _isLoadingColumns = true;
    _columnsError = null;
    notifyListeners();

    try {
      await _safeRequest((url) async {
        final uri = Uri.parse('$url/load-columns');
        final request = http.MultipartRequest('POST', uri);

        await _addPlatformFileToRequest(request, 'file', _dataFile!);

        final streamed = await request.send().timeout(timeout);
        final responseData = await streamed.stream.bytesToString();
        final jsonResponse = json.decode(responseData);

        if (streamed.statusCode == 200 && jsonResponse['columns'] is List) {
          _columns = List<String>.from(jsonResponse['columns']);
        } else {
          throw Exception(jsonResponse['error'] ?? 'Failed to load columns');
        }
      });
    } catch (e) {
      _columnsError = 'Network error: $e';
      _columns.clear();
    } finally {
      _isLoadingColumns = false;
      if (!_disposed) notifyListeners();
    }
  }

  // -------------------------------------------------------
  // Start Processing (with fallback)
  // -------------------------------------------------------
  Future<String?> startProcess({
    String? destinationFolder,
    Duration timeout = const Duration(seconds: 60),
  }) async {
    if (_isProcessing) return 'Processing already in progress';
    if (_dataFile == null || _documentFiles.isEmpty || _selectedColumn == null) {
      return 'Missing required files or selection';
    }

    _isProcessing = true;
    _progress = 0.0;
    _status = 'Starting...';
    _logs.clear();
    _combinedLogFile = null;
    _unmatchedValuesFile = null;
    _destFolder = destinationFolder;
    notifyListeners();

    try {
      await _safeRequest((url) async {
        final request = http.MultipartRequest(
          'POST',
          Uri.parse('$url/process'),
        );

        await _addPlatformFileToRequest(request, 'data_file', _dataFile!);

        for (final doc in _documentFiles) {
          await _addPlatformFileToRequest(request, 'documents', doc);
        }

        request.fields['selected_column'] = _selectedColumn!;
        request.fields['selected_color'] = _selectedColor;

        if (destinationFolder != null && destinationFolder.isNotEmpty) {
          request.fields['destination_folder'] = destinationFolder;
        }

        final streamed = await request.send().timeout(timeout);
        final data = await streamed.stream.bytesToString();
        final jsonResponse = json.decode(data);

        if (streamed.statusCode != 200) {
          throw Exception(jsonResponse['error'] ?? 'Failed to start');
        }
      });

      _startPolling();
      return null;
    } catch (e) {
      _isProcessing = false;
      _status = 'Failed to start: $e';
      notifyListeners();
      return _status;
    }
  }

  // -------------------------------------------------------
  // Polling (with fallback)
  // -------------------------------------------------------
  void _startPolling({Duration interval = const Duration(seconds: 1)}) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(interval, (_) => _fetchProgress());
  }

  Future<void> _fetchProgress() async {
    if (!_isProcessing) return;

    try {
      await _safeRequest((url) async {
        final resp = await _client
            .get(Uri.parse('$url/progress'))
            .timeout(const Duration(seconds: 10));

        if (resp.statusCode == 200) {
          final data = json.decode(resp.body);

          final prog = data['progress'];
          if (prog is num) _progress = prog.toDouble();

          _status = data['status'] ?? 'Processing...';
          _logs = List<Map<String, dynamic>>.from(data['logs'] ?? []);
          _combinedLogFile = data['combined_log'];
          _unmatchedValuesFile = data['unmatched_values'];

          if (_progress >= 100.0) {
            _isProcessing = false;
            _status = 'Completed';
            _pollTimer?.cancel();
          }

          notifyListeners();
        } else {
          throw Exception('Progress fetch failed');
        }
      });
    } catch (_) {
      _status = 'Connection issue... switching server';
      notifyListeners();
    }
  }

  // -------------------------------------------------------
  // Pause / Resume / Stop (with fallback)
  // -------------------------------------------------------
  Future<String?> pauseProcess() async {
    try {
      await _safeRequest(
        (url) => _client.post(Uri.parse('$url/pause')),
      );
      _status = 'Paused';
      notifyListeners();
      return null;
    } catch (e) {
      return 'Network error: $e';
    }
  }

  Future<String?> resumeProcess() async {
    try {
      await _safeRequest(
        (url) => _client.post(Uri.parse('$url/resume')),
      );
      _status = 'Resumed';
      notifyListeners();
      return null;
    } catch (e) {
      return 'Network error: $e';
    }
  }

  Future<String?> stopProcess() async {
    try {
      await _safeRequest(
        (url) => _client.post(Uri.parse('$url/stop')),
      );
      _isProcessing = false;
      _status = 'Stopped';
      _pollTimer?.cancel();
      notifyListeners();
      return null;
    } catch (e) {
      return 'Network error: $e';
    }
  }

  // -------------------------------------------------------
  // Downloads
  // -------------------------------------------------------
  String _safeFilename(String s) {
    return s.replaceAll(RegExp(r'[^a-zA-Z0-9 _\-\(\)]'), '');
  }

  Future<String?> downloadProcessedPdfs() async {
    if (_documentFiles.isEmpty) return 'No documents to download';

    try {
      for (int idx = 0; idx < _documentFiles.length; idx++) {
        final doc = _documentFiles[idx];
        final ext = doc.name.split('.').last;
        final base = doc.name.replaceAll('.$ext', '');
        final safeBase = _safeFilename(base);
        final processedName = '${safeBase}_${idx + 1}_Highlighted.$ext';

        await downloader.downloadFile(processedName, baseUrl);
      }
      return null;
    } catch (e) {
      return 'Download error: $e';
    }
  }

  Future<String?> downloadCombinedLog() async {
    if (_combinedLogFile == null) return 'No combined log';
    try {
      await downloader.downloadFile(_combinedLogFile!, baseUrl);
      return null;
    } catch (e) {
      return 'Download error: $e';
    }
  }

  Future<String?> downloadUnmatchedValues() async {
    if (_unmatchedValuesFile == null) return 'No unmatched values';
    try {
      await downloader.downloadFile(_unmatchedValuesFile!, baseUrl);
      return null;
    } catch (e) {
      return 'Download error: $e';
    }
  }

  // -------------------------------------------------------
  // Reset
  // -------------------------------------------------------
  void reset() {
    _dataFile = null;
    _documentFiles.clear();
    _columns.clear();
    _selectedColumn = null;
    _selectedColor = 'Yellow';
    _isLoadingColumns = false;
    _columnsError = null;
    _isProcessing = false;
    _progress = 0.0;
    _status = 'Idle';
    _logs.clear();
    _combinedLogFile = null;
    _unmatchedValuesFile = null;
    _destFolder = null;

    _pollTimer?.cancel();
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _pollTimer?.cancel();

    if (_ownsClient) {
      try {
        _client.close();
      } catch (_) {}
    }

    super.dispose();
  }
}
