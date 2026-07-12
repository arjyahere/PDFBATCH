
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';

import '../providers/highlighter_provider.dart';
import '../utils/error_handler.dart';

/// Screen for selecting data and document files
/// 
/// This is the first step in the batch highlighting workflow.
/// Users select a CSV/Excel data file and one or more PDF/DOCX documents.
class FileSelectionScreen extends StatelessWidget {
  const FileSelectionScreen({
    super.key,
    this.onNext,
  });

  final VoidCallback? onNext;

  /// Maximum file size in bytes (50 MB)
  static const int _maxFileSize = 50 * 1024 * 1024;

  /// Allowed data file extensions
  static const List<String> _allowedDataExtensions = ['csv', 'xlsx', 'xls'];

  /// Allowed document file extensions
  static const List<String> _allowedDocExtensions = ['pdf', 'docx'];

  /// Pick a data file (CSV or Excel)
  Future<void> _pickDataFile(BuildContext context) async {
    final provider = context.read<HighlighterProvider>();

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: _allowedDataExtensions,
        allowMultiple: false,
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      final file = result.files.first;

      // Validate file
      final validationError = _validateDataFile(file);
      if (validationError != null) {
        if (context.mounted) {
          ErrorHandler.showWarningSnackBar(context, validationError);
        }
        return;
      }

      provider.setDataFile(file);
      
      // Try loading columns automatically
      await provider.loadColumns();

      if (!context.mounted) return;
      
      ErrorHandler.showSuccessSnackBar(context, 'Data file selected: ${file.name}');
      if (provider.columnsError != null) {
        ErrorHandler.showErrorSnackBar(
          context,
          provider.columnsError!,
          retryAction: () => _pickDataFile(context),
        );
      } else if (provider.columns.isNotEmpty) {
        ErrorHandler.showSuccessSnackBar(
          context,
          'Loaded ${provider.columns.length} columns from data file',
        );
      }
    } catch (e) {
      if (context.mounted) {
        ErrorHandler.showErrorSnackBar(
          context,
          'Failed to pick data file: $e',
          retryAction: () => _pickDataFile(context),
        );
      }
    }
  }

  /// Validate data file
  String? _validateDataFile(PlatformFile file) {
    // Check file size
    if (file.size > _maxFileSize) {
      return 'File is too large. Maximum size is 50 MB.';
    }

    // Check extension
    final ext = file.extension?.toLowerCase() ?? '';
    if (!_allowedDataExtensions.contains(ext)) {
      return 'Invalid file type. Please select a CSV or Excel file.';
    }

    // Check if file has content
    if (file.size == 0) {
      return 'File is empty.';
    }

    return null;
  }

  /// Pick document files (PDF or DOCX)
  Future<void> _pickDocumentFiles(BuildContext context) async {
    final provider = context.read<HighlighterProvider>();

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: _allowedDocExtensions,
        allowMultiple: true,
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      int addedCount = 0;
      int skippedCount = 0;
      final List<String> errors = [];

      for (final file in result.files) {
        final validationError = _validateDocumentFile(file);
        if (validationError != null) {
          errors.add('${file.name}: $validationError');
          skippedCount++;
          continue;
        }

        // Check for duplicates
        if (provider.documentFiles.any((f) => f.name == file.name && f.size == file.size)) {
          errors.add('${file.name}: Already added');
          skippedCount++;
          continue;
        }

        provider.addDocumentFile(file);
        addedCount++;
      }

      if (!context.mounted) return;

      if (addedCount > 0) {
        ErrorHandler.showSuccessSnackBar(
          context,
          'Added $addedCount document(s)',
        );
      }

      if (skippedCount > 0 && errors.isNotEmpty) {
        // Show first error
        ErrorHandler.showWarningSnackBar(context, errors.first);
      }
    } catch (e) {
      if (context.mounted) {
        ErrorHandler.showErrorSnackBar(
          context,
          'Failed to pick document files: $e',
          retryAction: () => _pickDocumentFiles(context),
        );
      }
    }
  }

  /// Validate document file
  String? _validateDocumentFile(PlatformFile file) {
    // Check file size
    if (file.size > _maxFileSize) {
      return 'File is too large (max 50 MB)';
    }

    // Check extension
    final ext = file.extension?.toLowerCase() ?? '';
    if (!_allowedDocExtensions.contains(ext)) {
      return 'Invalid file type (PDF or DOCX only)';
    }

    // Check if file has content
    if (file.size == 0) {
      return 'File is empty';
    }

    return null;
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isSmallScreen = screenWidth < 600;
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

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
                      'Step 1: Select Files',
                      style: TextStyle(
                        fontSize: isSmallScreen ? 20 : 24,
                        fontWeight: FontWeight.bold,
                        color: colorScheme.onSurface,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Choose your data file (CSV or Excel) containing the values to highlight, '
                      'and select the document files (PDF or DOCX) to process.',
                      style: TextStyle(
                        fontSize: isSmallScreen ? 14 : 16,
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Data File Card
                    _buildDataFileCard(context, provider, isSmallScreen),
                    const SizedBox(height: 24),

                    // Document Files Card
                    _buildDocumentFilesCard(context, provider, isSmallScreen),
                    const SizedBox(height: 24),

                    // Manual Column Load Section
                    if (_showManualColumnLoad(provider))
                      _buildManualColumnLoadCard(context, provider),
                  ],
                ),
              ),
            ),

            // Navigation Buttons
            _buildNavigationButtons(context, provider),
          ],
        );
      },
    );
  }

  /// Check if manual column load section should be shown
  bool _showManualColumnLoad(HighlighterProvider provider) {
    return provider.dataFile != null &&
        provider.documentFiles.isNotEmpty &&
        provider.columns.isEmpty;
  }

  /// Build the data file selection card
  Widget _buildDataFileCard(
    BuildContext context,
    HighlighterProvider provider,
    bool isSmallScreen,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.table_chart, color: colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Data File',
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
              'Select a CSV or Excel file containing the values to search for.',
              style: TextStyle(color: colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 16),
            if (provider.dataFile != null) ...[
              _buildFileInfo(context, provider.dataFile!, isSmallScreen),
              const SizedBox(height: 12),
            ],
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => _pickDataFile(context),
                icon: const Icon(Icons.file_upload),
                label: Text(
                  provider.dataFile == null ? 'Choose Data File' : 'Change Data File',
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Supported: CSV, XLSX, XLS (max 50 MB)',
              style: TextStyle(
                color: colorScheme.onSurfaceVariant,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build file info display
  Widget _buildFileInfo(BuildContext context, PlatformFile file, bool isSmallScreen) {
    final sizeInKB = (file.size / 1024).toStringAsFixed(2);
    final sizeText = file.size > 1024 * 1024
        ? '${(file.size / (1024 * 1024)).toStringAsFixed(2)} MB'
        : '$sizeInKB KB';
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colorScheme.primaryContainer.withAlpha(128),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: colorScheme.primary.withAlpha(100)),
      ),
      child: Row(
        children: [
          Icon(Icons.insert_drive_file, color: colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  file.name,
                  style: TextStyle(
                    fontWeight: FontWeight.w500,
                    color: colorScheme.onSurface,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  'Size: $sizeText',
                  style: TextStyle(
                    color: colorScheme.onSurfaceVariant,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build the document files selection card
  Widget _buildDocumentFilesCard(
    BuildContext context,
    HighlighterProvider provider,
    bool isSmallScreen,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.description, color: Colors.orange),
                const SizedBox(width: 8),
                Text(
                  'Document Files',
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
              'Select PDF or DOCX files to highlight.',
              style: TextStyle(color: colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Text(
                    provider.documentFiles.isEmpty
                        ? 'No files selected'
                        : '${provider.documentFiles.length} file(s) selected',
                    style: TextStyle(
                      color: provider.documentFiles.isNotEmpty 
                          ? colorScheme.onSurface 
                          : colorScheme.onSurfaceVariant,
                      fontSize: isSmallScreen ? 14 : 16,
                      fontWeight: provider.documentFiles.isNotEmpty ? FontWeight.w500 : null,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: () => _pickDocumentFiles(context),
                icon: const Icon(Icons.file_upload),
                label: const Text('Add Document Files'),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Supported: PDF, DOCX (max 50 MB each)',
              style: TextStyle(
                color: colorScheme.onSurfaceVariant,
                fontSize: 12,
              ),
            ),
            if (provider.documentFiles.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 8),
              Text(
                'Selected files:',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 8),
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: provider.documentFiles.length,
                itemBuilder: (context, index) {
                  final file = provider.documentFiles[index];
                  return _buildDocumentListItem(context, provider, file, index);
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// Build a document list item
  Widget _buildDocumentListItem(
    BuildContext context,
    HighlighterProvider provider,
    PlatformFile file,
    int index,
  ) {
    final isPdf = file.extension?.toLowerCase() == 'pdf';
    final sizeInKB = (file.size / 1024).toStringAsFixed(2);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          isPdf ? Icons.picture_as_pdf : Icons.description,
          color: isPdf ? Colors.red : Colors.blue,
        ),
        title: Text(
          file.name,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(color: colorScheme.onSurface),
        ),
        subtitle: Text(
          '$sizeInKB KB • ${file.extension?.toUpperCase() ?? "Unknown"}',
          style: TextStyle(color: colorScheme.onSurfaceVariant),
        ),
        trailing: IconButton(
          icon: const Icon(Icons.delete_outline, color: Colors.red),
          onPressed: () {
            provider.removeDocumentFileAt(index);
            ErrorHandler.showInfoSnackBar(context, 'Removed ${file.name}');
          },
          tooltip: 'Remove file',
        ),
      ),
    );
  }

  /// Build the manual column load card
  Widget _buildManualColumnLoadCard(BuildContext context, HighlighterProvider provider) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      color: colorScheme.primaryContainer.withAlpha(128),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.table_chart_outlined, color: colorScheme.onSurface),
                const SizedBox(width: 8),
                Text(
                  'Load Columns',
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
              'Click below to load column names from your data file.',
              style: TextStyle(color: colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: provider.isLoadingColumns
                    ? null
                    : () async {
                        await provider.loadColumns();
                        if (!context.mounted) return;
                        if (provider.columnsError != null) {
                          ErrorHandler.showErrorSnackBar(
                            context,
                            provider.columnsError!,
                            retryAction: () async {
                              await provider.loadColumns();
                            },
                          );
                        } else if (provider.columns.isNotEmpty) {
                          ErrorHandler.showSuccessSnackBar(
                            context,
                            'Loaded ${provider.columns.length} columns',
                          );
                        }
                      },
                icon: provider.isLoadingColumns
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.refresh),
                label: Text(
                  provider.isLoadingColumns ? 'Loading...' : 'Load Columns',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Build the navigation buttons
  Widget _buildNavigationButtons(BuildContext context, HighlighterProvider provider) {
    final canProceed = provider.dataFile != null &&
        provider.documentFiles.isNotEmpty &&
        provider.columns.isNotEmpty;

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
          const Spacer(),
          Expanded(
            flex: 2,
            child: ElevatedButton.icon(
              onPressed: canProceed ? onNext : null,
              icon: const Icon(Icons.arrow_forward),
              label: const Text('Next'),
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
