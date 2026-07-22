import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../providers/highlighter_provider.dart';
import '../utils/error_handler.dart';

/// Screen for viewing detailed processing logs
/// 
/// Provides search, filtering, and detailed view of all processing logs.
class LogsScreen extends StatefulWidget {
  const LogsScreen({super.key});

  @override
  State<LogsScreen> createState() => _LogsScreenState();
}

class _LogsScreenState extends State<LogsScreen> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String _filterType = 'All'; // All, Matches, Errors, Info

  @override
  void initState() {
    super.initState();
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _searchController.removeListener(_onSearchChanged);
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    setState(() {
      _searchQuery = _searchController.text.toLowerCase();
    });
  }

  /// Filter logs based on current search and filter settings
  List<Map<String, dynamic>> _getFilteredLogs(HighlighterProvider provider) {
    var logs = List<Map<String, dynamic>>.from(provider.logs);

    // Apply type filter
    switch (_filterType) {
      case 'Matches':
        logs = logs.where((log) {
          final note = log['Note']?.toString().toLowerCase() ?? '';
          return note.contains('method') && !note.contains('error') && !note.contains('failed');
        }).toList();
        break;
      case 'Errors':
        logs = logs.where((log) {
          final note = log['Note']?.toString().toLowerCase() ?? '';
          return note.contains('error') || note.contains('failed');
        }).toList();
        break;
      case 'Info':
        logs = logs.where((log) {
          final note = log['Note']?.toString().toLowerCase() ?? '';
          return !note.contains('exact match') &&
              !note.contains('error') &&
              !note.contains('failed');
        }).toList();
        break;
    }

    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      logs = logs.where((log) {
        final file = log['File']?.toString().toLowerCase() ?? '';
        final value = log['Matched Value']?.toString().toLowerCase() ?? '';
        final note = log['Note']?.toString().toLowerCase() ?? '';
        final pair = log['Matched Pair']?.toString().toLowerCase() ?? '';
        return file.contains(_searchQuery) ||
            value.contains(_searchQuery) ||
            note.contains(_searchQuery) ||
            pair.contains(_searchQuery);
      }).toList();
    }

    return logs;
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isSmallScreen = screenWidth < 600;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Processing Logs'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: () => setState(() {}),
          ),
        ],
      ),
      body: Consumer<HighlighterProvider>(
        builder: (context, provider, child) {
          if (provider.logs.isEmpty) {
            return _buildEmptyState();
          }

          final filteredLogs = _getFilteredLogs(provider);

          return Column(
            children: [
              // Search and Filter Header
              _buildSearchHeader(isSmallScreen),

              // Summary
              _buildSummary(provider, filteredLogs, isSmallScreen),

              // Logs List
              Expanded(
                child: filteredLogs.isEmpty
                    ? _buildNoResults()
                    : _buildLogsList(filteredLogs, isSmallScreen),
              ),

              // Navigation Buttons
              _buildNavigationButtons(),
            ],
          );
        },
      ),
    );
  }

  /// Build empty state when no logs exist
  Widget _buildEmptyState() {
    return ErrorHandler.buildEmptyState(
      message: 'No logs available',
      subtitle: 'Start processing to generate logs',
      icon: Icons.list_alt,
    );
  }

  /// Build search and filter header
  Widget _buildSearchHeader(bool isSmallScreen) {
    return Container(
      padding: EdgeInsets.all(isSmallScreen ? 12 : 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          bottom: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Column(
        children: [
          // Search Bar
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'Search logs...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchQuery.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                      },
                    )
                  : null,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              filled: true,
              fillColor: Theme.of(context).colorScheme.surface,
              contentPadding: EdgeInsets.symmetric(
                horizontal: isSmallScreen ? 12 : 16,
                vertical: isSmallScreen ? 8 : 12,
              ),
            ),
            style: TextStyle(fontSize: isSmallScreen ? 14 : 16),
          ),
          const SizedBox(height: 12),
          
          // Filter Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: ['All', 'Matches', 'Errors', 'Info'].map((filter) {
                final isSelected = _filterType == filter;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: FilterChip(
                    label: Text(
                      filter,
                      style: TextStyle(
                        fontSize: isSmallScreen ? 12 : 14,
                        fontWeight: isSelected ? FontWeight.bold : null,
                      ),
                    ),
                    selected: isSelected,
                    onSelected: (selected) {
                      if (selected) {
                        setState(() {
                          _filterType = filter;
                        });
                      }
                    },
                    selectedColor: Theme.of(context).colorScheme.primaryContainer,
                    checkmarkColor: Theme.of(context).colorScheme.primary,
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  /// Build summary statistics
  Widget _buildSummary(
    HighlighterProvider provider,
    List<Map<String, dynamic>> filteredLogs,
    bool isSmallScreen,
  ) {
    final totalLogs = provider.logs.length;
    final matches = provider.logs.where((log) {
      final note = log['Note']?.toString().toLowerCase() ?? '';
      return note.contains('method') && !note.contains('error') && !note.contains('failed');
    }).length;
    final errors = provider.logs.where((log) {
      final note = log['Note']?.toString().toLowerCase() ?? '';
      return note.contains('error') || note.contains('failed');
    }).length;

    return Container(
      padding: EdgeInsets.all(isSmallScreen ? 12 : 16),
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: isSmallScreen
          ? Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _buildStatItem('Total', totalLogs.toString()),
                    ),
                    Expanded(
                      child: _buildStatItem('Filtered', filteredLogs.length.toString()),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: _buildStatItem('Matches', matches.toString(), Colors.green),
                    ),
                    Expanded(
                      child: _buildStatItem('Errors', errors.toString(), Colors.red),
                    ),
                  ],
                ),
              ],
            )
          : Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildStatItem('Total Logs', totalLogs.toString()),
                _buildStatItem('Filtered', filteredLogs.length.toString()),
                _buildStatItem('Matches', matches.toString(), Colors.green),
                _buildStatItem('Errors', errors.toString(), Colors.red),
              ],
            ),
    );
  }

  /// Build a single statistic item
  Widget _buildStatItem(String label, String value, [Color? valueColor]) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: valueColor,
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Colors.grey,
          ),
        ),
      ],
    );
  }

  /// Build no results message
  Widget _buildNoResults() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.search_off, size: 64, color: Colors.grey.shade400),
          const SizedBox(height: 16),
          const Text(
            'No logs match your filters',
            style: TextStyle(fontSize: 18, color: Colors.grey),
          ),
          const SizedBox(height: 8),
          Text(
            'Try adjusting your search or filters',
            style: TextStyle(color: Colors.grey.shade600),
          ),
        ],
      ),
    );
  }

  /// Build the logs list
  Widget _buildLogsList(List<Map<String, dynamic>> logs, bool isSmallScreen) {
    return ListView.builder(
      padding: EdgeInsets.symmetric(
        horizontal: isSmallScreen ? 8 : 16,
        vertical: 8,
      ),
      itemCount: logs.length,
      itemBuilder: (context, index) {
        final log = logs[index];
        return _buildLogCard(log, isSmallScreen);
      },
    );
  }

  /// Build a single log card
  Widget _buildLogCard(Map<String, dynamic> log, bool isSmallScreen) {
    final note = log['Note']?.toString() ?? '';
    final isMatch = note.toLowerCase().contains('method') && !note.toLowerCase().contains('error') && !note.toLowerCase().contains('failed');
    final isError = note.toLowerCase().contains('error') ||
        note.toLowerCase().contains('failed');

    Color avatarColor;
    IconData icon;
    if (isMatch) {
      avatarColor = Colors.green;
      icon = Icons.check;
    } else if (isError) {
      avatarColor = Colors.red;
      icon = Icons.error;
    } else {
      avatarColor = Colors.blue;
      icon = Icons.info;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () => _showLogDetails(log),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                backgroundColor: avatarColor,
                radius: isSmallScreen ? 16 : 20,
                child: Icon(
                  icon,
                  color: Colors.white,
                  size: isSmallScreen ? 16 : 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      log['File']?.toString() ?? 'Unknown file',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: isSmallScreen ? 14 : 16,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${log['Page/Paragraph']?.toString() ?? 'N/A'} • '
                      'Value: ${log['Matched Value']?.toString() ?? 'N/A'}',
                      style: TextStyle(
                        fontSize: isSmallScreen ? 11 : 12,
                        color: Colors.grey.shade700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      note,
                      style: TextStyle(
                        fontSize: isSmallScreen ? 11 : 12,
                        color: isError ? Colors.red : Colors.grey.shade600,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              if (!isSmallScreen)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      log['Column']?.toString() ?? '',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (log['Timestamp'] != null)
                      Text(
                        DateFormat('MM/dd HH:mm:ss').format(
                          DateTime.parse(log['Timestamp'].toString()),
                        ),
                        style: const TextStyle(
                          fontSize: 10,
                          color: Colors.grey,
                        ),
                      ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }

  /// Show log details in a dialog
  void _showLogDetails(Map<String, dynamic> log) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Log Details'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: log.entries.map((entry) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.key,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        color: Colors.grey,
                      ),
                    ),
                    Text(
                      entry.value?.toString() ?? 'N/A',
                      style: const TextStyle(fontSize: 14),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  /// Build navigation buttons
  Widget _buildNavigationButtons() {
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
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Back'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
