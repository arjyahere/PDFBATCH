import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import '../utils/download_helper.dart' as downloader;
import '../utils/error_handler.dart';

/// State management provider for the Batch Highlighter application
/// 
/// Manages the entire workflow from file selection through processing
/// to download. Handles API communication with server failover support.
class HighlighterProvider with ChangeNotifier {
  // ============================================================
  // Server & HTTP Configuration
  // ============================================================
  
  String baseUrl = AppConfig.defaultBaseUrl;

  int _activeServerIndex = 0;
  List<String> get _servers => AppConfig.baseUrls;

  final http.Client _client;
  final bool _ownsClient;

  Timer? _pollTimer;
  bool _disposed = false;

  /// Creates a new HighlighterProvider
  /// 
  /// Optionally accepts an HTTP client for dependency injection in tests.
  HighlighterProvider({http.Client? client})
      : _client = client ?? http.Client(),
        _ownsClient = client == null;

  // ============================================================
  // Safe Request With Server Fallback
  // ============================================================

  /// Executes a request with automatic server failover
  /// 
  /// Attempts the request on each configured server until one succeeds.
  /// Updates the active server index on successful request.
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
      } catch (e) {
        ErrorHandler.logError('Request failed for server $url', error: e);
        continue;
      }
    }

    throw Exception('All API servers are unreachable');
  }

  // ============================================================
  // Server Management
  // ============================================================

  /// Returns list of available server URLs
  List<String> get availableServers => List.unmodifiable(_servers);

  /// Manually set the active server by URL
  void setBaseUrl(String url) {
    final index = _servers.indexOf(url.trim());
    if (index != -1) {
      _activeServerIndex = index;
      baseUrl = _servers[index];
      ErrorHandler.logInfo('Server switched to: $baseUrl');
      notifyListeners();
    }
  }

  /// Set the active server by index
  void setBaseUrlByIndex(int index) {
    if (index >= 0 && index < _servers.length) {
      _activeServerIndex = index;
      baseUrl = _servers[index];
      ErrorHandler.logInfo('Server switched to index $index: $baseUrl');
      notifyListeners();
    }
  }

  // ============================================================
  // Application State
  // ============================================================
  
  PlatformFile? _dataFile;
  List<PlatformFile> _documentFiles = [];
  List<String> _columns = [];
  final List<String> _selectedColumns = [];
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

  /// Available highlight color options
  final List<String> colorOptions = [
    'Yellow',
    'Green',
    'Cyan',
    'Pink',
    'Blue',
    'Red',
  ];

  // ============================================================
  // Getters
  // ============================================================
  
  PlatformFile? get dataFile => _dataFile;
  List<PlatformFile> get documentFiles => List.unmodifiable(_documentFiles);
  List<String> get columns => List.unmodifiable(_columns);
  List<String> get selectedColumns => List.unmodifiable(_selectedColumns);
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

  // ============================================================
  // Setters
  // ============================================================
  
  /// Set the data file and reset dependent state
  void setDataFile(PlatformFile? file) {
    _dataFile = file;
    _columns.clear();
    _selectedColumns.clear();
    _columnsError = null;
    ErrorHandler.logInfo('Data file set: ${file?.name ?? "null"}');
    notifyListeners();
  }

  /// Set the list of document files
  void setDocumentFiles(List<PlatformFile> files) {
    _documentFiles = List.from(files);
    ErrorHandler.logInfo('Document files set: ${files.length} files');
    notifyListeners();
  }

  /// Toggle column selection (max 2 columns)
  void setSelectedColumn(String column, bool selected) {
    if (selected) {
      if (!_selectedColumns.contains(column) && _selectedColumns.length < 2) {
        _selectedColumns.add(column);
        ErrorHandler.logInfo('Column selected: $column');
      }
    } else {
      _selectedColumns.remove(column);
      ErrorHandler.logInfo('Column deselected: $column');
    }
    notifyListeners();
  }

  /// Clear all selected columns
  void clearSelectedColumns() {
    _selectedColumns.clear();
    ErrorHandler.logInfo('All columns cleared');
    notifyListeners();
  }

  /// Set the highlight color
  void setSelectedColor(String color) {
    if (colorOptions.contains(color)) {
      _selectedColor = color;
      ErrorHandler.logInfo('Color set: $color');
      notifyListeners();
    }
  }

  // ============================================================
  // Document File Management
  // ============================================================

  /// Add a single document file
  void addDocumentFile(PlatformFile file) {
    _documentFiles.add(file);
    ErrorHandler.logInfo('Document added: ${file.name}');
    notifyListeners();
  }

  /// Add multiple document files
  void addMultipleDocumentFiles(List<PlatformFile> files) {
    _documentFiles.addAll(files);
    ErrorHandler.logInfo('${files.length} documents added');
    notifyListeners();
  }

  /// Remove a document file by index
  void removeDocumentFileAt(int index) {
    if (index >= 0 && index < _documentFiles.length) {
      final removed = _documentFiles.removeAt(index);
      ErrorHandler.logInfo('Document removed: ${removed.name}');
      notifyListeners();
    }
  }

  /// Clear all document files
  void clearDocumentFiles() {
    _documentFiles.clear();
    ErrorHandler.logInfo('All documents cleared');
    notifyListeners();
  }

  // ============================================================
  // File Download
  // ============================================================
  
  /// Download a single file by name
  Future<String?> downloadFile(String fileName) async {
    try {
      ErrorHandler.logInfo('Downloading file: $fileName');
      await downloader.downloadFile(fileName, baseUrl);
      return null;
    } catch (e) {
      ErrorHandler.logError('Download failed for $fileName', error: e);
      return 'Download error: $e';
    }
  }

  // ============================================================
  // HTTP Helpers
  // ============================================================
  
  /// Add a PlatformFile to a multipart request
  /// 
  /// Handles both web (bytes) and native (path) file sources
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

  // ============================================================
  // Load Columns
  // ============================================================
  
  /// Load column names from the data file
  /// 
  /// Sends the data file to the server and retrieves column names.
  Future<void> loadColumns({Duration? timeout}) async {
    if (_dataFile == null) {
      _columnsError = 'No data file selected';
      notifyListeners();
      return;
    }

    _isLoadingColumns = true;
    _columnsError = null;
    notifyListeners();

    try {
      await _safeRequest((url) async {
        final uri = Uri.parse('$url/load-columns');
        final request = http.MultipartRequest('POST', uri);

        await _addPlatformFileToRequest(request, 'file', _dataFile!);

        final streamed = await request.send().timeout(
          timeout ?? AppConfig.defaultTimeout,
        );
        final responseData = await streamed.stream.bytesToString();
        final jsonResponse = json.decode(responseData) as Map<String, dynamic>;

        if (streamed.statusCode == 200 && jsonResponse['columns'] is List) {
          _columns = List<String>.from(jsonResponse['columns'] as List<dynamic>);
          ErrorHandler.logInfo('Columns loaded: ${_columns.length} columns');
        } else {
          throw Exception(jsonResponse['error'] ?? 'Failed to load columns');
        }
      });
    } catch (e) {
      _columnsError = 'Failed to load columns: $e';
      _columns.clear();
      ErrorHandler.logError('Column loading failed', error: e);
    } finally {
      _isLoadingColumns = false;
      if (!_disposed) notifyListeners();
    }
  }

  // ============================================================
  // Process Management
  // ============================================================
  
  /// Start the batch highlighting process
  /// 
  /// Uploads files and configuration to the server and begins processing.
  Future<String?> startProcess({
    String? destinationFolder,
    Duration? timeout,
  }) async {
    if (_isProcessing) return 'Processing already in progress';
    if (_dataFile == null) return 'No data file selected';
    if (_documentFiles.isEmpty) return 'No document files selected';
    if (_selectedColumns.isEmpty) return 'No columns selected';

    _isProcessing = true;
    _progress = 0.0;
    _status = 'Starting...';
    _logs.clear();
    _combinedLogFile = null;
    _unmatchedValuesFile = null;
    _destFolder = destinationFolder;
    notifyListeners();

    ErrorHandler.logInfo('Starting process with ${_documentFiles.length} documents');

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

        request.fields['selected_columns'] = _selectedColumns.join(',');
        request.fields['selected_color'] = _selectedColor;

        if (destinationFolder != null && destinationFolder.isNotEmpty) {
          request.fields['destination_folder'] = destinationFolder;
        }

        final streamed = await request.send().timeout(
          timeout ?? AppConfig.uploadTimeout,
        );
        final data = await streamed.stream.bytesToString();
        final jsonResponse = json.decode(data) as Map<String, dynamic>;

        if (streamed.statusCode != 200) {
          final error = jsonResponse['error'];
          if (error is Map<String, dynamic>) {
            throw Exception(json.encode(error));
          } else {
            throw Exception(error?.toString() ?? 'Failed to start');
          }
        }
      });

      _startPolling();
      return null;
    } catch (e) {
      _isProcessing = false;
      _status = 'Failed to start: $e';
      ErrorHandler.logError('Process start failed', error: e);
      notifyListeners();
      return _status;
    }
  }

  // ============================================================
  // Progress Polling
  // ============================================================
  
  /// Start polling for progress updates
  void _startPolling({Duration? interval}) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(
      interval ?? AppConfig.progressPollingInterval,
      (_) => _fetchProgress(),
    );
    ErrorHandler.logInfo('Progress polling started');
  }

  /// Fetch current progress from the server
  Future<void> _fetchProgress() async {
    if (!_isProcessing) return;

    try {
      await _safeRequest((url) async {
        final resp = await _client
            .get(Uri.parse('$url/progress'))
            .timeout(const Duration(seconds: 10));

        if (resp.statusCode == 200) {
          final data = json.decode(resp.body) as Map<String, dynamic>;

          final prog = data['progress'];
          if (prog is num) _progress = prog.toDouble().clamp(0.0, 100.0);

          _status = data['status']?.toString() ?? 'Processing...';
          _logs = List<Map<String, dynamic>>.from(
            (data['logs'] as List<dynamic>?) ?? [],
          );
          _combinedLogFile = data['combined_log']?.toString();
          _unmatchedValuesFile = data['unmatched_values']?.toString();

          if (_progress >= 100.0) {
            _isProcessing = false;
            _status = 'Completed';
            _pollTimer?.cancel();
            ErrorHandler.logInfo('Processing completed');
          }

          notifyListeners();
        } else {
          throw Exception('Progress fetch failed: ${resp.statusCode}');
        }
      });
    } catch (e) {
      _status = 'Connection issue... switching server';
      ErrorHandler.logError('Progress fetch failed', error: e);
      notifyListeners();
    }
  }

  // ============================================================
  // Process Control
  // ============================================================
  
  /// Pause the current process
  Future<String?> pauseProcess() async {
    try {
      await _safeRequest(
        (url) => _client.post(Uri.parse('$url/pause')),
      );
      _status = 'Paused';
      ErrorHandler.logInfo('Process paused');
      notifyListeners();
      return null;
    } catch (e) {
      ErrorHandler.logError('Pause failed', error: e);
      return 'Failed to pause: $e';
    }
  }

  /// Resume a paused process
  Future<String?> resumeProcess() async {
    try {
      await _safeRequest(
        (url) => _client.post(Uri.parse('$url/resume')),
      );
      _status = 'Resumed';
      _startPolling();
      ErrorHandler.logInfo('Process resumed');
      notifyListeners();
      return null;
    } catch (e) {
      ErrorHandler.logError('Resume failed', error: e);
      return 'Failed to resume: $e';
    }
  }

  /// Stop the current process
  Future<String?> stopProcess() async {
    try {
      await _safeRequest(
        (url) => _client.post(Uri.parse('$url/stop')),
      );
      _isProcessing = false;
      _status = 'Stopped';
      _pollTimer?.cancel();
      ErrorHandler.logInfo('Process stopped');
      notifyListeners();
      return null;
    } catch (e) {
      ErrorHandler.logError('Stop failed', error: e);
      return 'Failed to stop: $e';
    }
  }

  // ============================================================
  // Batch Downloads
  // ============================================================
  
  /// Sanitize a filename for safe file system operations
  String _safeFilename(String s) {
    return s.replaceAll(RegExp(r'[^a-zA-Z0-9 _\-\(\)]'), '');
  }

  /// Download all processed PDFs
  Future<String?> downloadProcessedPdfs() async {
    if (_documentFiles.isEmpty) return 'No documents to download';

    ErrorHandler.logInfo('Downloading ${_documentFiles.length} processed documents');

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
      ErrorHandler.logError('Download processed PDFs failed', error: e);
      return 'Download error: $e';
    }
  }

  /// Download the combined log file
  Future<String?> downloadCombinedLog() async {
    if (_combinedLogFile == null) return 'No combined log available';
    try {
      await downloader.downloadFile(_combinedLogFile!, baseUrl);
      return null;
    } catch (e) {
      ErrorHandler.logError('Download combined log failed', error: e);
      return 'Download error: $e';
    }
  }

  /// Download the unmatched values file
  Future<String?> downloadUnmatchedValues() async {
    if (_unmatchedValuesFile == null) return 'No unmatched values file available';
    try {
      await downloader.downloadFile(_unmatchedValuesFile!, baseUrl);
      return null;
    } catch (e) {
      ErrorHandler.logError('Download unmatched values failed', error: e);
      return 'Download error: $e';
    }
  }

  // ============================================================
  // Reset
  // ============================================================
  
  /// Reset all state to initial values
  void reset() {
    _dataFile = null;
    _documentFiles.clear();
    _columns.clear();
    _selectedColumns.clear();
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
    ErrorHandler.logInfo('Provider state reset');
    notifyListeners();
  }

  // ============================================================
  // Cleanup
  // ============================================================
  
  @override
  void dispose() {
    _disposed = true;
    _pollTimer?.cancel();

    if (_ownsClient) {
      try {
        _client.close();
      } catch (_) {
        // Ignore close errors
      }
    }

    super.dispose();
  }
}
