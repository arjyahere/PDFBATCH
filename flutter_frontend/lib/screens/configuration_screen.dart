import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/highlighter_provider.dart';

class ConfigurationScreen extends StatelessWidget {
  const ConfigurationScreen({
    super.key,
    this.onBack,
    this.onNext,
  });

  final VoidCallback? onBack;
  final VoidCallback? onNext;

  @override
  Widget build(BuildContext context) {
    return Consumer<HighlighterProvider>(
      builder: (context, provider, child) {
        if (provider.columns.isEmpty) {
          return const Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.table_chart, size: 64, color: Colors.grey),
                SizedBox(height: 16),
                Text(
                  'No columns available',
                  style: TextStyle(fontSize: 18, color: Colors.grey),
                ),
                SizedBox(height: 8),
                Text(
                  'Please go back and load columns from your data file',
                  style: TextStyle(color: Colors.grey),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          );
        }

        return Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Step 2: Configure Highlighting',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Choose a highlight color first, then select the column containing the values to highlight.',
                      style: TextStyle(fontSize: 16),
                    ),
                    const SizedBox(height: 24),

                    // Color Selection (First)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Select Highlight Color',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Choose the color to use for highlighting matched text in the documents.',
                              style: TextStyle(color: Colors.grey),
                            ),
                            const SizedBox(height: 16),
                            LayoutBuilder(
                              builder: (context, constraints) {
                                final screenWidth = MediaQuery.of(context).size.width;
                                final crossAxisCount = screenWidth > 600 ? 4 : (screenWidth > 400 ? 3 : 2);

                                return GridView.builder(
                                  shrinkWrap: true,
                                  physics: const NeverScrollableScrollPhysics(),
                                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                                    crossAxisCount: crossAxisCount,
                                    crossAxisSpacing: 12,
                                    mainAxisSpacing: 12,
                                    childAspectRatio: screenWidth > 400 ? 2.5 : 2.0,
                                  ),
                                  itemCount: provider.colorOptions.length,
                                  itemBuilder: (context, index) {
                                    final color = provider.colorOptions[index];
                                    final isSelected = provider.selectedColor == color;

                                    return InkWell(
                                      onTap: () => provider.setSelectedColor(color),
                                      borderRadius: BorderRadius.circular(8),
                                      child: Container(
                                        decoration: BoxDecoration(
                                          color: _getColorValue(color),
                                          borderRadius: BorderRadius.circular(8),
                                          border: Border.all(
                                            color: isSelected ? Colors.black : Colors.transparent,
                                            width: 3,
                                          ),
                                          boxShadow: isSelected
                                              ? [
                                                  BoxShadow(
                                                    color: Colors.black.withValues(alpha: 0.3),
                                                    blurRadius: 4,
                                                    offset: const Offset(0, 2),
                                                  )
                                                ]
                                              : null,
                                        ),
                                        child: Center(
                                          child: Text(
                                            color,
                                            style: TextStyle(
                                              color: _getTextColor(color),
                                              fontWeight: FontWeight.w600,
                                              fontSize: screenWidth > 400 ? 14 : 12,
                                            ),
                                          ),
                                        ),
                                      ),
                                    );
                                  },
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: 24),

                    // Column Selection (Second)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Select Column',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Choose the column from your data file that contains the values to search for in the documents.',
                              style: TextStyle(color: Colors.grey),
                            ),
                            const SizedBox(height: 16),
                            DropdownButtonFormField<String>(
                              initialValue: provider.selectedColumn,
                              decoration: const InputDecoration(
                                border: OutlineInputBorder(),
                                contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                              ),
                              hint: const Text('Select a column'),
                              items: provider.columns.map((column) {
                                return DropdownMenuItem<String>(
                                  value: column,
                                  child: Text(column),
                                );
                              }).toList(),
                              onChanged: (String? value) {
                                provider.setSelectedColumn(value);
                              },
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Please select a column';
                                }
                                return null;
                              },
                            ),
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: 24),

                    // Configuration Summary
                    if (provider.selectedColumn != null)
                      Card(
                        color: Theme.of(context).colorScheme.primaryContainer,
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Configuration Summary',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 16),
                              _buildSummaryItem('Data File', provider.dataFile?.name ?? 'Unknown'),
                              _buildSummaryItem('Documents', '${provider.documentFiles.length} file(s)'),
                              _buildSummaryItem('Column', provider.selectedColumn!),
                              _buildSummaryItem('Highlight Color', provider.selectedColor),
                              const SizedBox(height: 16),
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: _getColorValue(provider.selectedColor).withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(
                                    color: _getColorValue(provider.selectedColor),
                                    width: 2,
                                  ),
                                ),
                                child: Row(
                                  children: [
                                    Icon(
                                      Icons.check_circle,
                                      color: _getColorValue(provider.selectedColor),
                                    ),
                                    const SizedBox(width: 12),
                                    const Expanded(
                                      child: Text(
                                        'Configuration complete! Proceed to the next step to start processing.',
                                        style: TextStyle(fontWeight: FontWeight.w500),
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
                      onPressed: onBack ?? () => Navigator.of(context).pop(),
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
                      onPressed: provider.selectedColumn != null ? onNext : null,
                      icon: const Icon(Icons.arrow_forward),
                      label: const Text('Next'),
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

  Widget _buildSummaryItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }

  Color _getColorValue(String colorName) {
    switch (colorName) {
      case 'Yellow':
        return Colors.yellow;
      case 'Green':
        return Colors.green;
      case 'Cyan':
        return Colors.cyan;
      case 'Pink':
        return Colors.pink;
      case 'Blue':
        return Colors.blue;
      case 'Red':
        return Colors.red;
      default:
        return Colors.yellow;
    }
  }

  Color _getTextColor(String colorName) {
    switch (colorName) {
      case 'Yellow':
      case 'Cyan':
      case 'Pink':
        return Colors.black;
      default:
        return Colors.white;
    }
  }
}
