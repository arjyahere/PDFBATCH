import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import '../providers/highlighter_provider.dart';
import '../utils/error_handler.dart';

import 'package:file_selector/file_selector.dart' show getDirectoryPath;


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

  Future<void> _selectDestinationFolder() async {
    if (kIsWeb) {
      // On web, show a message that folder selection is not supported
      if (mounted) {
        ErrorHandler.showInfoSnackBar(
          context,
          'Folder selection is not supported on web. Files will be downloaded to your default download folder.',
        );
      }
      return;
    }

    try {
      final String? selectedDirectory = await getDirectoryPath();
      if (selectedDirectory != null && mounted) {
        setState(() {
          _destinationController.text = selectedDirectory;
        });
      }
    } catch (e) {
      if (mounted) {
        ErrorHandler.showErrorSnackBar(
          context,
          'Error selecting folder: $e',
          retryAction: _selectDestinationFolder,
        );
      }
    }
  }

  @override
  void dispose() {
    _destinationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isSmallScreen = screenWidth < 600;

    return Consumer<HighlighterProvider>(
      builder: (context, provider, child) {
        return Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding: EdgeInsets.all(isSmallScreen ? 12 : 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Step 3: Process & Download',
                      style: TextStyle(
                        fontSize: isSmallScreen ? 20 : 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Start the batch highlighting process and monitor progress. Download the processed files and logs when complete.',
                      style: TextStyle(fontSize: isSmallScreen ? 14 : 16),
                    ),
                    const SizedBox(height: 24),

              // Process Controls
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Processing Controls',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Destination Folder Selection
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _destinationController,
                              decoration: const InputDecoration(
                                labelText: 'Destination Folder (Optional)',
                                hintText: 'Leave empty for default location',
                                border: OutlineInputBorder(),
                                prefixIcon: Icon(Icons.folder),
                              ),
                              enabled: !provider.isProcessing,
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                             onPressed: !provider.isProcessing && !kIsWeb ? _selectDestinationFolder : null,
                             icon: const Icon(Icons.folder_open),
                             tooltip: kIsWeb ? 'Not supported on web' : 'Select Folder',
                           ),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // Control Buttons
                      if (isSmallScreen)
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            ElevatedButton.icon(
                              onPressed: (provider.selectedColumn != null && !provider.isProcessing)
                                  ? () async {
                                      final error = await provider.startProcess(
                                        destinationFolder: _destinationController.text.trim().isEmpty
                                            ? null
                                            : _destinationController.text.trim(),
                                      );
                                      if (error != null && mounted) {
                                        // ignore: use_build_context_synchronously
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                            content: Text('Error: $error'),
                                            backgroundColor: Colors.red,
                                          ),
                                        );
                                      }
                                    }
                                  : null,
                              icon: const Icon(Icons.play_arrow),
                              label: const Text('Start Processing'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.green,
                                foregroundColor: Colors.white,
                              ),
                            ),
                            if (provider.isProcessing) ...[
                              const SizedBox(height: 8),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                                children: [
                                  IconButton(
                                    onPressed: () async {
                                      final error = await provider.pauseProcess();
                                      if (error != null && mounted) {
                                        // ignore: use_build_context_synchronously
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(content: Text('Error: $error')),
                                        );
                                      }
                                    },
                                    icon: const Icon(Icons.pause),
                                    tooltip: 'Pause',
                                  ),
                                  IconButton(
                                    onPressed: () async {
                                      final error = await provider.resumeProcess();
                                      if (error != null && mounted) {
                                        // ignore: use_build_context_synchronously
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(content: Text('Error: $error')),
                                        );
                                      }
                                    },
                                    icon: const Icon(Icons.play_arrow),
                                    tooltip: 'Resume',
                                  ),
                                  IconButton(
                                    onPressed: () async {
                                      final error = await provider.stopProcess();
                                      if (error != null && mounted) {
                                        ErrorHandler.showErrorSnackBar(context, error);
                                      }
                                    },
                                    icon: const Icon(Icons.stop),
                                    tooltip: 'Stop',
                                    color: Colors.red,
                                  ),
                                ],
                              ),
                            ],
                          ],
                        )
                      else
                        Row(
                          children: [
                            Expanded(
                              child: ElevatedButton.icon(
                                onPressed: (provider.selectedColumn != null && !provider.isProcessing)
                                    ? () async {
                                        final error = await provider.startProcess(
                                          destinationFolder: _destinationController.text.trim().isEmpty
                                              ? null
                                              : _destinationController.text.trim(),
                                        );
                                        if (error != null && mounted) {
                                          ErrorHandler.showErrorSnackBar(
                                            context,
                                            error,
                                            retryAction: () async {
                                              final retryError = await provider.startProcess(
                                                destinationFolder: _destinationController.text.trim().isEmpty
                                                    ? null
                                                    : _destinationController.text.trim(),
                                              );
                                              if (retryError != null) {
                                                if (mounted) {
                                                  ErrorHandler.showErrorSnackBar(context, retryError);
                                                }
                                              }
                                            },
                                          );
                                        }
                                      }
                                    : null,
                                icon: const Icon(Icons.play_arrow),
                                label: const Text('Start Processing'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.green,
                                  foregroundColor: Colors.white,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            if (provider.isProcessing) ...[
                              IconButton(
                                onPressed: () async {
                                  final error = await provider.pauseProcess();
                                  if (error != null && mounted) {
                                    ErrorHandler.showErrorSnackBar(context, error);
                                  }
                                },
                                icon: const Icon(Icons.pause),
                                tooltip: 'Pause',
                              ),
                              IconButton(
                                onPressed: () async {
                                  final error = await provider.resumeProcess();
                                  if (error != null && mounted) {
                                    ErrorHandler.showErrorSnackBar(context, error);
                                  }
                                },
                                icon: const Icon(Icons.play_arrow),
                                tooltip: 'Resume',
                              ),
                              IconButton(
                                onPressed: () async {
                                  final error = await provider.stopProcess();
                                  if (error != null && mounted) {
                                    ErrorHandler.showErrorSnackBar(context, error);
                                  }
                                },
                                icon: const Icon(Icons.stop),
                                tooltip: 'Stop',
                                color: Colors.red,
                              ),
                            ],
                          ],
                        ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // Progress Display
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Text(
                            'Progress',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const Spacer(),
                          Text(
                            '${provider.progress.toStringAsFixed(1)}%',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      LinearProgressIndicator(
                        value: provider.progress / 100,
                        backgroundColor: Colors.grey[300],
                        valueColor: AlwaysStoppedAnimation<Color>(
                          provider.progress >= 100 ? Colors.green : Colors.blue,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        provider.status,
                        style: TextStyle(
                          color: provider.status.contains('Error') || provider.status == 'Stopped'
                              ? Colors.red
                              : provider.progress >= 100
                                  ? Colors.green
                                  : Colors.black,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // Logs Preview
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: const Text(
                              'Processing Logs',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          TextButton.icon(
                            onPressed: provider.logs.isNotEmpty
                                ? () => Navigator.pushNamed(context, '/logs')
                                : null,
                            icon: const Icon(Icons.list),
                            label: const Text('View All'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      if (provider.logs.isEmpty)
                        const Center(
                          child: Padding(
                            padding: EdgeInsets.all(32),
                            child: Text(
                              'No logs yet. Start processing to see results.',
                              style: TextStyle(color: Colors.grey),
                              textAlign: TextAlign.center,
                            ),
                          ),
                        )
                      else
                        SizedBox(
                          height: 200,
                          child: ListView.builder(
                            itemCount: provider.logs.length,
                            itemBuilder: (context, index) {
                              final log = provider.logs[provider.logs.length - 1 - index]; // Show latest first
                              return ListTile(
                                dense: true,
                                leading: Icon(
                                  log['Note']?.contains('Exact match') == true
                                      ? Icons.check_circle
                                      : log['Note']?.contains('Error') == true
                                          ? Icons.error
                                          : Icons.info,
                                  color: log['Note']?.contains('Exact match') == true
                                      ? Colors.green
                                      : log['Note']?.contains('Error') == true
                                          ? Colors.red
                                          : Colors.blue,
                                  size: 20,
                                ),
                                title: Text(
                                  log['File'] ?? '',
                                  style: const TextStyle(fontSize: 14),
                                ),
                                subtitle: Text(
                                  '${log['Page/Paragraph'] ?? ''} • ${log['Matched Value'] ?? 'N/A'}',
                                  style: const TextStyle(fontSize: 12),
                                ),
                                trailing: Text(
                                  log['Timestamp'] != null
                                      ? DateFormat('HH:mm:ss').format(DateTime.parse(log['Timestamp']))
                                      : '',
                                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                                ),
                              );
                            },
                          ),
                        ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // Download Section
              if (provider.progress >= 100)
                Card(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Download Results',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Processing complete! Download the highlighted documents, logs, and unmatched values.',
                        ),
                        const SizedBox(height: 16),

                        // Download Processed PDFs Button
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: () async {
                              final error = await provider.downloadProcessedPdfs();
                              if (error != null && mounted) {
                                ErrorHandler.showErrorSnackBar(context, error);
                              } else if (mounted) {
                                ErrorHandler.showSuccessSnackBar(
                                  context,
                                  'Processed PDFs are available in the destination folder. Check the logs for specific file locations.',
                                );
                              }
                            },
                            icon: const Icon(Icons.download),
                            label: const Text('Download Processed PDFs'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                              foregroundColor: Colors.white,
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),

                        if (provider.combinedLogFile != null)
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: () async {
                                final error = await provider.downloadFile(provider.combinedLogFile!);
                                if (error != null && mounted) {
                                  ErrorHandler.showErrorSnackBar(context, error);
                                } else if (mounted) {
                                  ErrorHandler.showSuccessSnackBar(context, 'Combined log downloaded successfully.');
                                }
                              },
                              icon: const Icon(Icons.download),
                              label: const Text('Download Combined Log (CSV)'),
                            ),
                          ),
                        const SizedBox(height: 8),
                        if (provider.unmatchedValuesFile != null)
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: () async {
                                final error = await provider.downloadFile(provider.unmatchedValuesFile!);
                                if (!mounted) return;
                                if (error != null) {
                                  ErrorHandler.showErrorSnackBar(context, error);
                                } else {
                                  ErrorHandler.showSuccessSnackBar(context, 'Unmatched values downloaded successfully.');
                                }
                              },
                              icon: const Icon(Icons.download),
                              label: const Text('Download Unmatched Values (CSV)'),
                            ),
                          ),
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.green.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.green),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.check_circle, color: Colors.green),
                              SizedBox(width: 12),
                              Expanded(
                                child: Text(
                                  'All processed files are available in the destination folder. Check the logs for specific file locations.',
                                  style: TextStyle(color: Colors.green),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
            ),

            // Navigation Buttons
            Container(
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
                      onPressed: widget.onBack ?? () => Navigator.of(context).pop(),
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
                      onPressed: provider.progress >= 100 ? (widget.onViewLogs ?? () => Navigator.of(context).pushNamed('/logs')) : null,
                      icon: const Icon(Icons.list),
                      label: const Text('View Logs'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
