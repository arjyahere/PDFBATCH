import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import '../providers/highlighter_provider.dart';
import '../utils/error_handler.dart';

class FileSelectionScreen extends StatelessWidget {
  const FileSelectionScreen({
    super.key,
    this.onNext,
  });

  final VoidCallback? onNext;

  Future<void> _pickDataFile(BuildContext context) async {
    final provider = context.read<HighlighterProvider>();

    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv', 'xlsx', 'xls'],
        allowMultiple: false,
      );

      if (result == null || result.files.isEmpty) return;

      provider.setDataFile(result.files.first);

      // Try loading columns safely
      await provider.loadColumns();

      if (provider.columnsError != null && context.mounted) {
        ErrorHandler.showErrorSnackBar(
          context,
          provider.columnsError!,
          retryAction: () => _pickDataFile(context),
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

  Future<void> _pickDocumentFiles(BuildContext context) async {
    final provider = context.read<HighlighterProvider>();

    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'docx'],
        allowMultiple: true,
      );

      if (result == null || result.files.isEmpty) return;

      for (var file in result.files) {
        provider.addDocumentFile(file);
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
                      'Step 1: Select Files',
                      style: TextStyle(
                        fontSize: isSmallScreen ? 20 : 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Choose your data file (CSV or Excel) containing the values to highlight, and select the document files (PDF or DOCX) to process.',
                      style: TextStyle(fontSize: isSmallScreen ? 14 : 16),
                    ),
                    const SizedBox(height: 24),

              // ------------------- DATA FILE CARD -------------------
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Data File',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Select a CSV or Excel file containing the values to search for.',
                        style: TextStyle(color: Colors.grey),
                      ),
                      const SizedBox(height: 16),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            provider.dataFile?.name ?? 'No file selected',
                            style: TextStyle(
                              color: provider.dataFile != null ? Colors.black : Colors.grey,
                              fontSize: isSmallScreen ? 14 : 16,
                            ),
                          ),
                          const SizedBox(height: 8),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: () => _pickDataFile(context),
                              icon: const Icon(Icons.file_upload),
                              label: Text(isSmallScreen ? 'Choose File' : 'Choose Data File'),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        provider.dataFile != null
                            ? 'Size: ${(provider.dataFile!.size / 1024).toStringAsFixed(2)} KB'
                            : 'Size: Unknown',
                        style: const TextStyle(color: Colors.grey, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // ------------------- DOCUMENT FILES CARD -------------------
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Document Files',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Select PDF or DOCX files to highlight.',
                        style: TextStyle(color: Colors.grey),
                      ),
                      const SizedBox(height: 16),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            provider.documentFiles.isEmpty
                                ? 'No files selected'
                                : '${provider.documentFiles.length} file(s) selected',
                            style: TextStyle(
                              color: provider.documentFiles.isNotEmpty ? Colors.black : Colors.grey,
                              fontSize: isSmallScreen ? 14 : 16,
                            ),
                          ),
                          const SizedBox(height: 8),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: () => _pickDocumentFiles(context),
                              icon: const Icon(Icons.file_upload),
                              label: const Text('Add Document Files'),
                            ),
                          ),
                        ],
                      ),
                      if (provider.documentFiles.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        const Text(
                          'Selected files:',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        ListView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: provider.documentFiles.length,
                          itemBuilder: (context, index) {
                            final file = provider.documentFiles[index]; // Null safety guard

                            return Card(
                              margin: const EdgeInsets.only(bottom: 8),
                              child: ListTile(
                                leading: Icon(
                                  file.extension == 'pdf'
                                      ? Icons.picture_as_pdf
                                      : Icons.description,
                                  color: file.extension == 'pdf' ? Colors.red : Colors.blue,
                                ),
                                title: Text(file.name),
                                subtitle: Text(
                                  '${(file.size / 1024).toStringAsFixed(2)} KB • ${file.extension?.toUpperCase() ?? ''}',
                                ),
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete, color: Colors.red),
                                  onPressed: () => provider.removeDocumentFileAt(index),
                                ),
                              ),
                            );
                          },
                        ),
                      ],
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // ------------------- MANUAL COLUMN LOAD -------------------
              if (provider.dataFile != null &&
                  provider.documentFiles.isNotEmpty &&
                  provider.columns.isEmpty)
                Card(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Manual Column Loading',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'If columns didn\'t load automatically, click "Load Columns" to try again.',
                        ),
                        const SizedBox(height: 16),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: provider.isLoadingColumns
                                ? null
                                : () async {
                                  await provider.loadColumns();
                                  if (provider.columnsError != null && context.mounted) {
                                    ErrorHandler.showErrorSnackBar(
                                      context,
                                      provider.columnsError!,
                                      retryAction: () async {
                                        await provider.loadColumns();
                                        if (provider.columnsError != null && context.mounted) {
                                          ErrorHandler.showErrorSnackBar(context, provider.columnsError!);
                                        }
                                      },
                                    );
                                  }
                                },
                            icon: provider.isLoadingColumns
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.table_chart),
                            label: Text(
                              provider.isLoadingColumns ? 'Loading...' : 'Load Columns',
                            ),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 16),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

              // ------------------- ERROR MESSAGE -------------------
              if (provider.columnsError != null)
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.error,
                            color: Theme.of(context).colorScheme.error),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Text(
                            provider.columnsError!,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.error,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

              // ------------------- COLUMNS DISPLAY -------------------
              if (provider.columns.isNotEmpty)
                Card(
                  color: Theme.of(context).colorScheme.secondaryContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Available Columns',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: provider.columns
                              .map((column) => Chip(label: Text(column)))
                              .toList(),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Columns loaded successfully! Proceed to the next step.',
                          style: TextStyle(color: Colors.green),
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
                  const Spacer(),
                  ElevatedButton.icon(
                    onPressed: provider.dataFile != null && provider.documentFiles.isNotEmpty && provider.columns.isNotEmpty
                        ? onNext
                        : null,
                    icon: const Icon(Icons.arrow_forward),
                    label: const Text('Next'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 24),
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
