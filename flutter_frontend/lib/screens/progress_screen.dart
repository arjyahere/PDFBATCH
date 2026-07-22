import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:file_selector/file_selector.dart' show getDirectoryPath;

import '../providers/highlighter_provider.dart';
import '../utils/error_handler.dart';

/// Screen for processing and monitoring batch highlighting
/// 
/// This is the third and final step in the workflow.
/// Users can start processing, monitor progress, and download results.
class ProgressScreen extends StatefulWidget {
  const ProgressScreen({
    super.key,
    this.onBack,
    this.onViewLogs,
  });

  final VoidCallback? onBack;
  final VoidCallback? onViewLogs;

  @override
  State<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends State<ProgressScreen> {
  final TextEditingController _destinationController = TextEditingController();
  bool _isDownloading = false;

  @override
  void dispose() {
    _destinationController.dispose();
    super.dispose();
  }

  /// Select destination folder for downloads (desktop only)
  Future<void> _selectDestinationFolder() async {
    if (kIsWeb) {
      if (mounted) {
        ErrorHandler.showInfoSnackBar(
          context,
          'Folder selection is not supported on web. Files will download to your default downloads folder.',
        );
      }
      return;
    }

    try {
      final selectedDirectory = await getDirectoryPath();
      if (!mounted) return;
      
      if (selectedDirectory != null) {
        setState(() {
          _destinationController.text = selectedDirectory;
        });
        ErrorHandler.showSuccessSnackBar(
          context,
          'Destination folder selected',
        );
      }
    } catch (e) {
      if (!mounted) return;
      ErrorHandler.showErrorSnackBar(
        context,
        'Error selecting folder: $e',
        retryAction: _selectDestinationFolder,
      );
    }
  }

  /// Start the processing
  Future<void> _startProcessing(HighlighterProvider provider) async {
    final error = await provider.startProcess(
      destinationFolder: _destinationController.text.trim().isEmpty
          ? null
          : _destinationController.text.trim(),
    );
    
    if (!mounted) return;
    
    if (error != null) {
      ErrorHandler.showErrorSnackBar(
        context,
        error,
        retryAction: () => _startProcessing(provider),
      );
    } else {
      ErrorHandler.showSuccessSnackBar(
        context,
        'Processing started successfully',
      );
    }
  }

  /// Pause processing
  Future<void> _pauseProcessing(HighlighterProvider provider) async {
    final error = await provider.pauseProcess();
    if (!mounted) return;
    
    if (error != null) {
      ErrorHandler.showErrorSnackBar(context, error);
    } else {
      ErrorHandler.showInfoSnackBar(context, 'Processing paused');
    }
  }

  /// Resume processing
  Future<void> _resumeProcessing(HighlighterProvider provider) async {
    final error = await provider.resumeProcess();
    if (!mounted) return;
    
    if (error != null) {
      ErrorHandler.showErrorSnackBar(context, error);
    } else {
      ErrorHandler.showSuccessSnackBar(context, 'Processing resumed');
    }
  }

  /// Stop processing
  Future<void> _stopProcessing(HighlighterProvider provider) async {
    final confirmed = await _showStopConfirmation();
    if (!confirmed || !mounted) return;

    final error = await provider.stopProcess();
    if (!mounted) return;
    
    if (error != null) {
      ErrorHandler.showErrorSnackBar(context, error);
    } else {
      ErrorHandler.showInfoSnackBar(context, 'Processing stopped');
    }
  }

  /// Show stop confirmation dialog
  Future<bool> _showStopConfirmation() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Stop Processing?'),
        content: const Text(
          'Are you sure you want to stop the current processing? '
          'This will cancel all pending operations.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            child: const Text('Stop'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  /// Download processed documents
  Future<void> _downloadProcessed(HighlighterProvider provider) async {
    if (provider.outputFiles.isEmpty) {
      ErrorHandler.showInfoSnackBar(
        context,
        'No processed documents available',
      );
      return;
    }
    
    setState(() => _isDownloading = true);
    
    final error = await provider.downloadProcessedPdfs();
    
    setState(() => _isDownloading = false);
    
    if (!mounted) return;
    
    if (error != null) {
      ErrorHandler.showErrorSnackBar(
        context,
        error,
        retryAction: () => _downloadProcessed(provider),
      );
    } else {
      ErrorHandler.showSuccessSnackBar(
        context,
        'Highlighted PDFs downloaded successfully',
      );
    }
  }

  /// Download combined log
  Future<void> _downloadLog(HighlighterProvider provider) async {
    if (provider.combinedLogFile == null) {
      ErrorHandler.showInfoSnackBar(
        context,
        'Matches log not available',
      );
      return;
    }
    
    setState(() => _isDownloading = true);
    
    final error = await provider.downloadFile(provider.combinedLogFile!);
    
    setState(() => _isDownloading = false);
    
    if (!mounted) return;
    
    if (error != null) {
      ErrorHandler.showErrorSnackBar(context, error);
    } else {
      ErrorHandler.showSuccessSnackBar(
        context,
        'Matches log downloaded successfully',
      );
    }
  }

  /// Download unmatched values
  Future<void> _downloadUnmatched(HighlighterProvider provider) async {
    if (provider.unmatchedValuesFile == null) {
      ErrorHandler.showInfoSnackBar(
        context,
        'Missing values report not available',
      );
      return;
    }
    
    setState(() => _isDownloading = true);
    
    final error = await provider.downloadFile(provider.unmatchedValuesFile!);
    
    setState(() => _isDownloading = false);
    
    if (!mounted) return;
    
    if (error != null) {
      ErrorHandler.showErrorSnackBar(context, error);
    } else {
      ErrorHandler.showSuccessSnackBar(
        context,
        'Missing values report downloaded successfully',
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isSmallScreen = screenWidth < 600;

    return Consumer<HighlighterProvider>(
      builder: (context, provider, child) {
        return Stack(
          children: [
            Column(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    padding: EdgeInsets.all(isSmallScreen ? 12 : 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHeader(context, isSmallScreen),
                        const SizedBox(height: 16),

                        // Large File Warning (shown when processing large files)
                        if (provider.isLargeFile && provider.isProcessing)
                          _buildLargeFileWarning(context, provider),
                        if (provider.isLargeFile && provider.isProcessing)
                          const SizedBox(height: 16),

                        // Processing Controls
                        _buildControlsCard(context, provider, isSmallScreen),
                        const SizedBox(height: 24),

                        // Progress Display
                        _buildProgressCard(context, provider),
                        const SizedBox(height: 24),

                        // Logs Preview
                        _buildLogsPreviewCard(context, provider, isSmallScreen),
                        const SizedBox(height: 24),

                        // Download Section (shown when complete)
                        if (provider.progress >= 100)
                          _buildDownloadCard(context, provider),
                      ],
                    ),
                  ),
                ),

                // Navigation Buttons
                _buildNavigationButtons(context, provider),
              ],
            ),
            
            // Loading overlay during downloads
            if (_isDownloading)
              const ColoredBox(
                color: Colors.black54,
                child: Center(
                  child: CircularProgressIndicator(),
                ),
              ),
          ],
        );
      },
    );
  }

  /// Build the screen header
  Widget _buildHeader(BuildContext context, bool isSmallScreen) {
    final colorScheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Step 3: Process & Download',
          style: TextStyle(
            fontSize: isSmallScreen ? 20 : 24,
            fontWeight: FontWeight.bold,
            color: colorScheme.onSurface,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Start the batch highlighting process and monitor progress. '
          'Download the processed files and logs when complete.',
          style: TextStyle(
            fontSize: isSmallScreen ? 14 : 16,
            color: colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  /// Build large file warning banner
  Widget _buildLargeFileWarning(BuildContext context, HighlighterProvider provider) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.orange.withOpacity(0.15),
        border: Border.all(color: Colors.orange.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            Icons.access_time,
            color: Colors.orange.shade700,
            size: 28,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Large File - Processing May Take Time',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: Colors.orange.shade800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  provider.getLargeFileWarningMessage(),
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.orange.shade700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build the controls card
  Widget _buildControlsCard(
    BuildContext context,
    HighlighterProvider provider,
    bool isSmallScreen,
  ) {
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.settings, color: colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Processing Controls',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: colorScheme.onSurface,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Destination Folder Selection
            if (!kIsWeb)
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _destinationController,
                      style: TextStyle(color: colorScheme.onSurface),
                      decoration: InputDecoration(
                        labelText: 'Destination Folder (Optional)',
                        hintText: 'Leave empty for default location',
                        labelStyle: TextStyle(color: colorScheme.onSurfaceVariant),
                        hintStyle: TextStyle(color: colorScheme.onSurfaceVariant.withAlpha(128)),
                        border: const OutlineInputBorder(),
                        prefixIcon: Icon(Icons.folder, color: colorScheme.onSurfaceVariant),
                        enabled: !provider.isProcessing,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: !provider.isProcessing
                        ? _selectDestinationFolder
                        : null,
                    icon: const Icon(Icons.folder_open),
                    tooltip: 'Select Folder',
                  ),
                ],
              ),
            if (!kIsWeb) const SizedBox(height: 16),

            // Control Buttons
            _buildControlButtons(context, provider, isSmallScreen),
          ],
        ),
      ),
    );
  }

  /// Build control buttons
  Widget _buildControlButtons(
    BuildContext context,
    HighlighterProvider provider,
    bool isSmallScreen,
  ) {
    final canStart = provider.selectedColumns.isNotEmpty &&
        !provider.isProcessing;

    if (isSmallScreen) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ElevatedButton.icon(
            onPressed: canStart ? () => _startProcessing(provider) : null,
            icon: const Icon(Icons.play_arrow),
            label: const Text('Start Processing'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
          ),
          if (provider.isProcessing) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                IconButton(
                  onPressed: () => _pauseProcessing(provider),
                  icon: const Icon(Icons.pause),
                  tooltip: 'Pause',
                ),
                IconButton(
                  onPressed: () => _resumeProcessing(provider),
                  icon: const Icon(Icons.play_arrow),
                  tooltip: 'Resume',
                ),
                IconButton(
                  onPressed: () => _stopProcessing(provider),
                  icon: const Icon(Icons.stop),
                  tooltip: 'Stop',
                  color: Colors.red,
                ),
              ],
            ),
          ],
        ],
      );
    }

    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: canStart ? () => _startProcessing(provider) : null,
            icon: const Icon(Icons.play_arrow),
            label: const Text('Start Processing'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
          ),
        ),
        if (provider.isProcessing) ...[
          const SizedBox(width: 8),
          IconButton(
            onPressed: () => _pauseProcessing(provider),
            icon: const Icon(Icons.pause),
            tooltip: 'Pause',
          ),
          IconButton(
            onPressed: () => _resumeProcessing(provider),
            icon: const Icon(Icons.play_arrow),
            tooltip: 'Resume',
          ),
          IconButton(
            onPressed: () => _stopProcessing(provider),
            icon: const Icon(Icons.stop),
            tooltip: 'Stop',
            color: Colors.red,
          ),
        ],
      ],
    );
  }

  /// Build the progress card
  Widget _buildProgressCard(BuildContext context, HighlighterProvider provider) {
    final isComplete = provider.progress >= 100;
    final hasError = provider.status.toLowerCase().contains('error') ||
        provider.status.toLowerCase().contains('failed');
    final isStopped = provider.status.toLowerCase().contains('stopped');
    final colorScheme = Theme.of(context).colorScheme;

    Color progressColor;
    if (hasError || isStopped) {
      progressColor = Colors.red;
    } else if (isComplete) {
      progressColor = Colors.green;
    } else {
      progressColor = colorScheme.primary;
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.trending_up, color: colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Progress',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: colorScheme.onSurface,
                  ),
                ),
                const Spacer(),
                Text(
                  '${provider.progress.toStringAsFixed(1)}%',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: progressColor,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: provider.progress / 100,
                backgroundColor: colorScheme.surfaceContainerHighest,
                valueColor: AlwaysStoppedAnimation<Color>(progressColor),
                minHeight: 8,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(
                  hasError
                      ? Icons.error
                      : isComplete
                          ? Icons.check_circle
                          : Icons.info,
                  color: progressColor,
                  size: 16,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    provider.status,
                    style: TextStyle(
                      color: hasError || isComplete || isStopped
                          ? progressColor
                          : colorScheme.onSurface,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// Build the logs preview card
  Widget _buildLogsPreviewCard(BuildContext context, HighlighterProvider provider, bool isSmallScreen) {
    final colorScheme = Theme.of(context).colorScheme;
    final totalLogs = provider.logs.length;
    
    // Match: any successful highlight (contains 'highlight', 'match', or 'exact match')
    // but NOT error-related notes
    final matchCount = provider.logs.where((log) {
      final note = log['Note']?.toString().toLowerCase() ?? '';
      final isMatchNote = note.contains('highlight') || 
                          note.contains('match') || 
                          note.contains('exact match');
      final isErrorNote = note.contains('error') || 
                          note.contains('failed') || 
                          note.contains('skip');
      // Also check if there's an error code
      final hasErrorCode = log['Error Code'] != null && log['Error Code'].toString().isNotEmpty;
      return isMatchNote && !isErrorNote && !hasErrorCode;
    }).length;
    
    // Error: notes containing error/failed/skip OR has error code
    final errorCount = provider.logs.where((log) {
      final note = log['Note']?.toString().toLowerCase() ?? '';
      final hasErrorCode = log['Error Code'] != null && log['Error Code'].toString().isNotEmpty;
      return note.contains('error') || 
             note.contains('failed') || 
             note.contains('skip') ||
             hasErrorCode;
    }).length;
    
    // Info: all other logs (skipped, unsupported, etc.)
    final infoCount = totalLogs - matchCount - errorCount;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.list_alt, color: colorScheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Processing Logs',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: colorScheme.onSurface,
                    ),
                  ),
                ),
                if (totalLogs > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      '$totalLogs entries',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: provider.logs.isNotEmpty
                      ? widget.onViewLogs ??
                          () => Navigator.pushNamed(context, '/logs')
                      : null,
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('View All'),
                ),
              ],
            ),
            if (totalLogs > 0) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                children: [
                  _buildLogStatChip(
                    context,
                    icon: Icons.check_circle,
                    label: '$matchCount matches',
                    color: Colors.green,
                  ),
                  _buildLogStatChip(
                    context,
                    icon: Icons.error,
                    label: '$errorCount errors',
                    color: Colors.red,
                  ),
                  _buildLogStatChip(
                    context,
                    icon: Icons.info,
                    label: '$infoCount info',
                    color: colorScheme.primary,
                  ),
                ],
              ),
            ],
            const SizedBox(height: 16),
            if (provider.logs.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    children: [
                      Icon(Icons.article_outlined, size: 48, color: colorScheme.onSurfaceVariant),
                      const SizedBox(height: 8),
                      Text(
                        'No logs yet. Start processing to see results.',
                        style: TextStyle(color: colorScheme.onSurfaceVariant),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              )
            else
              SizedBox(
                height: 200,
                child: ListView.builder(
                  itemCount: provider.logs.length.clamp(0, 10),
                  itemBuilder: (context, index) {
                    // Show latest first
                    final logIndex = provider.logs.length - 1 - index;
                    final log = provider.logs[logIndex];
                    return _buildLogItem(context, log, isSmallScreen);
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Build a single log item
  Widget _buildLogItem(BuildContext context, Map<String, dynamic> log, bool isSmallScreen) {
    final note = log['Note']?.toString() ?? '';
    final noteLower = note.toLowerCase();
    
    // Match: any successful highlight (contains 'highlight', 'match', or 'exact match')
    // but NOT error-related notes
    final isMatchNote = noteLower.contains('highlight') || 
                        noteLower.contains('match') || 
                        noteLower.contains('exact match');
    final isErrorNote = noteLower.contains('error') || 
                        noteLower.contains('failed') || 
                        noteLower.contains('skip');
    // Also check if there's an error code
    final hasErrorCode = log['Error Code'] != null && log['Error Code'].toString().isNotEmpty;
    
    final isMatch = isMatchNote && !isErrorNote && !hasErrorCode;
    final isError = isErrorNote || hasErrorCode;
    
    final colorScheme = Theme.of(context).colorScheme;

    IconData icon;
    Color color;
    if (isMatch) {
      icon = Icons.check_circle;
      color = Colors.green;
    } else if (isError) {
      icon = Icons.error;
      color = Colors.red;
    } else {
      icon = Icons.info;
      color = colorScheme.primary;
    }

    return ListTile(
      dense: true,
      leading: Icon(icon, color: color, size: 20),
      title: Text(
        log['File']?.toString() ?? 'Unknown',
        style: TextStyle(
          fontSize: 14,
          color: colorScheme.onSurface,
        ),
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        '${log['Page/Paragraph']?.toString() ?? ''} • '
        '${log['Matched Pair']?.toString() ?? log['Matched Value']?.toString() ?? 'N/A'}',
        style: TextStyle(
          fontSize: 12,
          color: colorScheme.onSurfaceVariant,
        ),
        overflow: TextOverflow.ellipsis,
      ),
      trailing: log['Timestamp'] != null
          ? Text(
              DateFormat('HH:mm:ss').format(
                DateTime.parse(log['Timestamp'].toString()),
              ),
              style: TextStyle(
                fontSize: 12,
                color: colorScheme.onSurfaceVariant,
              ),
            )
          : null,
    );
  }

  /// Build a log statistics chip
  Widget _buildLogStatChip(
    BuildContext context, {
    required IconData icon,
    required String label,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withAlpha(25),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withAlpha(50)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  /// Build the download card
  Widget _buildDownloadCard(BuildContext context, HighlighterProvider provider) {
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      color: colorScheme.primaryContainer.withAlpha(128),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.download_done, color: colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Download Results',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: colorScheme.onSurface,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Processing complete! Download your highlighted documents and reports.',
              style: TextStyle(color: colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 16),

            // Download Processed Documents
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: provider.outputFiles.isNotEmpty 
                    ? () => _downloadProcessed(provider)
                    : null,
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text('Download Highlighted PDFs'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            const SizedBox(height: 8),

            // Download Matches Log
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: provider.combinedLogFile != null
                    ? () => _downloadLog(provider)
                    : null,
                icon: const Icon(Icons.description),
                label: const Text('Download Matches (CSV)'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
            const SizedBox(height: 8),

            // Download Missing Values
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: provider.unmatchedValuesFile != null
                    ? () => _downloadUnmatched(provider)
                    : null,
                icon: const Icon(Icons.find_in_page),
                label: const Text('Download Missing Values (CSV)'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build navigation buttons
  Widget _buildNavigationButtons(BuildContext context, HighlighterProvider provider) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        border: Border(
          top: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: provider.isProcessing
                  ? null
                  : widget.onBack ?? () => Navigator.of(context).pop(),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Back'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: provider.progress >= 100
                  ? widget.onViewLogs ??
                      () => Navigator.pushNamed(context, '/logs')
                  : null,
              icon: const Icon(Icons.list),
              label: const Text('View Logs'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
