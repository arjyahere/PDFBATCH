import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/highlighter_provider.dart';
import '../utils/error_handler.dart';

/// Screen for configuring highlighting options
/// 
/// This is the second step in the batch highlighting workflow.
/// Users select the highlight color and choose columns to search.
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
        // Show empty state if no columns available
        if (provider.columns.isEmpty) {
          return _buildEmptyState(context);
        }

        return Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildHeader(),
                    const SizedBox(height: 24),

                    // Color Selection
                    _buildColorSelectionCard(context, provider),
                    const SizedBox(height: 24),

                    // Column Selection
                    _buildColumnSelectionCard(context, provider),
                    const SizedBox(height: 24),

                    // Configuration Summary
                    if (provider.selectedColumns.isNotEmpty)
                      _buildSummaryCard(context, provider),
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

  /// Build empty state when no columns are loaded
  Widget _buildEmptyState(BuildContext context) {
    return ErrorHandler.buildEmptyState(
      message: 'No columns available',
      subtitle: 'Please go back and load columns from your data file',
      icon: Icons.table_chart_outlined,
      onAction: onBack,
      actionLabel: 'Go Back',
    );
  }

  /// Build the screen header
  Widget _buildHeader() {
    return const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Step 2: Configure Highlighting',
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        SizedBox(height: 8),
        Text(
          'Choose a highlight color and select the columns containing the values to highlight.',
          style: TextStyle(fontSize: 16),
        ),
      ],
    );
  }

  /// Build the color selection card
  Widget _buildColorSelectionCard(BuildContext context, HighlighterProvider provider) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.palette, color: Colors.purple),
                SizedBox(width: 8),
                Text(
                  'Select Highlight Color',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
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
                final crossAxisCount = screenWidth > 600
                    ? 4
                    : (screenWidth > 400 ? 3 : 2);

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
                    return _buildColorOption(context, provider, color);
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  /// Build a single color option
  Widget _buildColorOption(
    BuildContext context,
    HighlighterProvider provider,
    String color,
  ) {
    final isSelected = provider.selectedColor == color;
    final colorValue = _getColorValue(color);
    final textColor = _getTextColor(color);

    return InkWell(
      onTap: () => provider.setSelectedColor(color),
      borderRadius: BorderRadius.circular(8),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: colorValue,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? Colors.black : Colors.transparent,
            width: 3,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: Colors.black.withAlpha(77),
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
              color: textColor,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }

  /// Build the column selection card
  Widget _buildColumnSelectionCard(BuildContext context, HighlighterProvider provider) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.view_column, color: Colors.green),
                SizedBox(width: 8),
                Text(
                  'Select Columns',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Select up to 2 columns from your data file that contain the values to search for.',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 16),
            
            // Column 1 Dropdown
            _buildColumnDropdown(
              context,
              provider,
              label: 'Column 1 (Required)',
              hint: 'Select first column',
              currentValue: provider.selectedColumns.isNotEmpty
                  ? provider.selectedColumns[0]
                  : null,
              onChanged: (value) {
                if (value != null) {
                  _handleColumn1Selection(provider, value);
                }
              },
            ),
            const SizedBox(height: 16),
            
            // Column 2 Dropdown
            _buildColumnDropdown(
              context,
              provider,
              label: 'Column 2 (Optional)',
              hint: 'Select second column (optional)',
              currentValue: provider.selectedColumns.length > 1
                  ? provider.selectedColumns[1]
                  : null,
              onChanged: (value) {
                _handleColumn2Selection(provider, value);
              },
              enabled: provider.selectedColumns.isNotEmpty,
            ),
            
            // Validation message
            if (provider.selectedColumns.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Please select at least 1 column to continue',
                  style: TextStyle(color: Colors.red, fontSize: 14),
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Build a column dropdown
  Widget _buildColumnDropdown(
    BuildContext context,
    HighlighterProvider provider, {
    required String label,
    required String hint,
    required String? currentValue,
    required ValueChanged<String?> onChanged,
    bool enabled = true,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: currentValue,
          isExpanded: true,
          decoration: InputDecoration(
            border: const OutlineInputBorder(),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            enabled: enabled,
          ),
          hint: Text(hint),
          items: provider.columns.map((column) {
            // Disable already selected columns (except current)
            final isSelected = provider.selectedColumns.contains(column) &&
                column != currentValue;
            
            return DropdownMenuItem<String>(
              value: column,
              enabled: !isSelected,
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      column,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: isSelected ? Colors.grey : null,
                      ),
                    ),
                  ),
                  if (isSelected)
                    const Icon(Icons.check, size: 16, color: Colors.grey),
                ],
              ),
            );
          }).toList(),
          onChanged: enabled ? onChanged : null,
        ),
      ],
    );
  }

  /// Handle column 1 selection
  void _handleColumn1Selection(HighlighterProvider provider, String value) {
    if (provider.selectedColumns.isEmpty) {
      provider.setSelectedColumn(value, true);
    } else {
      // Preserve column 2 if it exists and is different
      final oldColumn2 = provider.selectedColumns.length > 1
          ? provider.selectedColumns[1]
          : null;
      
      provider.clearSelectedColumns();
      provider.setSelectedColumn(value, true);
      
      // Restore column 2 if valid
      if (oldColumn2 != null && oldColumn2 != value) {
        provider.setSelectedColumn(oldColumn2, true);
      }
    }
  }

  /// Handle column 2 selection
  void _handleColumn2Selection(HighlighterProvider provider, String? value) {
    if (value == null) {
      // Remove column 2 if it exists
      if (provider.selectedColumns.length > 1) {
        final column2 = provider.selectedColumns[1];
        provider.setSelectedColumn(column2, false);
      }
    } else {
      // Ensure column 1 exists first
      if (provider.selectedColumns.isEmpty) {
        ErrorHandler.logError('Attempted to set column 2 without column 1');
        return;
      }
      
      // Don't allow same column twice
      if (provider.selectedColumns[0] == value) {
        ErrorHandler.logInfo('Cannot select the same column twice');
        return;
      }
      
      // Set column 2
      if (provider.selectedColumns.length < 2) {
        provider.setSelectedColumn(value, true);
      } else {
        // Replace column 2
        final column1 = provider.selectedColumns[0];
        provider.clearSelectedColumns();
        provider.setSelectedColumn(column1, true);
        provider.setSelectedColumn(value, true);
      }
    }
  }

  /// Build the configuration summary card
  Widget _buildSummaryCard(BuildContext context, HighlighterProvider provider) {
    return Card(
      color: Theme.of(context).colorScheme.primaryContainer.withAlpha(128),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.summarize),
                SizedBox(width: 8),
                Text(
                  'Configuration Summary',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _buildSummaryItem('Data File', provider.dataFile?.name ?? 'Unknown'),
            _buildSummaryItem('Documents', '${provider.documentFiles.length} file(s)'),
            _buildSummaryItem('Columns', provider.selectedColumns.join(', ')),
            _buildSummaryItem('Highlight Color', provider.selectedColor),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _getColorValue(provider.selectedColor).withAlpha(51),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: _getColorValue(provider.selectedColor),
                  width: 2,
                ),
              ),
              child: const Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.green),
                  SizedBox(width: 12),
                  Expanded(
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
    );
  }

  /// Build a summary item row
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
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
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
              onPressed: provider.selectedColumns.isNotEmpty ? onNext : null,
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

  /// Get the color value for a color name
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

  /// Get the text color for a color name
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
