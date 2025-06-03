import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/highlighter_provider.dart';

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
    _searchController.addListener(() {
      setState(() {
        _searchQuery = _searchController.text.toLowerCase();
      });
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> _getFilteredLogs(HighlighterProvider provider) {
    var logs = provider.logs;

    // Apply type filter
    switch (_filterType) {
      case 'Matches':
        logs = logs.where((log) => log['Note']?.contains('Exact match') == true).toList();
        break;
      case 'Errors':
        logs = logs.where((log) => log['Note']?.contains('Error') == true || log['Note']?.contains('Failed') == true).toList();
        break;
      case 'Info':
        logs = logs.where((log) =>
            log['Note']?.contains('Exact match') != true &&
            log['Note']?.contains('Error') != true &&
            log['Note']?.contains('Failed') != true).toList();
        break;
    }

    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      logs = logs.where((log) {
        final file = log['File']?.toLowerCase() ?? '';
        final value = log['Matched Value']?.toLowerCase() ?? '';
        final note = log['Note']?.toLowerCase() ?? '';
        return file.contains(_searchQuery) ||
               value.contains(_searchQuery) ||
               note.contains(_searchQuery);
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
      ),
      body: Consumer<HighlighterProvider>(
        builder: (context, provider, child) {
          final filteredLogs = _getFilteredLogs(provider);

          if (provider.logs.isEmpty) {
            return Column(
              children: [
                Expanded(
                  child: const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.list_alt, size: 64, color: Colors.grey),
                        SizedBox(height: 16),
                        Text(
                          'No logs available',
                          style: TextStyle(fontSize: 18, color: Colors.grey),
                        ),
                        SizedBox(height: 8),
                        Text(
                          'Start processing to generate logs',
                          style: TextStyle(color: Colors.grey),
                          textAlign: TextAlign.center,
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
                ),
              ],
            );
          }

          return Column(
            children: [
              // Search and Filter Header
              Container(
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
                    const SizedBox(height: 8),
                    // Filter Chips
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: ['All', 'Matches', 'Errors', 'Info'].map((filter) {
                          return Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: FilterChip(
                              label: Text(filter, style: TextStyle(fontSize: isSmallScreen ? 12 : 14)),
                              selected: _filterType == filter,
                              onSelected: (selected) {
                                if (selected) {
                                  setState(() {
                                    _filterType = filter;
                                  });
                                }
                              },
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                  ],
                ),
              ),

              // Summary
              Container(
                padding: EdgeInsets.all(isSmallScreen ? 12 : 16),
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                child: isSmallScreen
                    ? Column(
                        children: [
                          Row(
                            children: [
                              Expanded(child: _buildSummaryItem('Total Logs', provider.logs.length.toString())),
                              const SizedBox(width: 16),
                              Expanded(child: _buildSummaryItem('Filtered', filteredLogs.length.toString())),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: _buildSummaryItem(
                                  'Matches',
                                  provider.logs.where((log) => log['Note']?.contains('Exact match') == true).length.toString(),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: _buildSummaryItem(
                                  'Errors',
                                  provider.logs.where((log) => log['Note']?.contains('Error') == true || log['Note']?.contains('Failed') == true).length.toString(),
                                ),
                              ),
                            ],
                          ),
                        ],
                      )
                    : Row(
                        children: [
                          _buildSummaryItem('Total Logs', provider.logs.length.toString()),
                          const SizedBox(width: 24),
                          _buildSummaryItem('Filtered', filteredLogs.length.toString()),
                          const SizedBox(width: 24),
                          _buildSummaryItem(
                            'Matches',
                            provider.logs.where((log) => log['Note']?.contains('Exact match') == true).length.toString(),
                          ),
                          const SizedBox(width: 24),
                          _buildSummaryItem(
                            'Errors',
                            provider.logs.where((log) => log['Note']?.contains('Error') == true || log['Note']?.contains('Failed') == true).length.toString(),
                          ),
                        ],
                      ),
              ),

              // Logs List
              Expanded(
                child: filteredLogs.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.search_off, size: 64, color: Colors.grey),
                            const SizedBox(height: 16),
                            const Text(
                              'No logs match your filters',
                              style: TextStyle(fontSize: 18, color: Colors.grey),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        itemCount: filteredLogs.length,
                        itemBuilder: (context, index) {
                          final log = filteredLogs[index];
                          final isMatch = log['Note']?.contains('Exact match') == true;
                          final isError = log['Note']?.contains('Error') == true || log['Note']?.contains('Failed') == true;

                          return Card(
                            margin: EdgeInsets.symmetric(
                              horizontal: isSmallScreen ? 4 : 8,
                              vertical: 4,
                            ),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: isMatch
                                    ? Colors.green
                                    : isError
                                        ? Colors.red
                                        : Colors.blue,
                                child: Icon(
                                  isMatch
                                      ? Icons.check
                                      : isError
                                          ? Icons.error
                                          : Icons.info,
                                  color: Colors.white,
                                  size: isSmallScreen ? 16 : 20,
                                ),
                              ),
                              title: Text(
                                log['File'] ?? 'Unknown file',
                                style: TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: isSmallScreen ? 14 : 16,
                                ),
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${log['Page/Paragraph'] ?? 'N/A'} • Value: ${log['Matched Value'] ?? 'N/A'}',
                                    style: TextStyle(fontSize: isSmallScreen ? 11 : 12),
                                  ),
                                  Text(
                                    log['Note'] ?? 'No details',
                                    style: TextStyle(
                                      fontSize: isSmallScreen ? 11 : 12,
                                      color: isError ? Colors.red : Colors.grey[600],
                                    ),
                                  ),
                                ],
                              ),
                              trailing: isSmallScreen
                                  ? null
                                  : Column(
                                      mainAxisAlignment: MainAxisAlignment.center,
                                      crossAxisAlignment: CrossAxisAlignment.end,
                                      children: [
                                        Text(
                                          log['Column'] ?? '',
                                          style: const TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                        Text(
                                          log['Timestamp'] != null
                                              ? DateFormat('MM/dd HH:mm:ss').format(DateTime.parse(log['Timestamp']))
                                              : '',
                                          style: const TextStyle(fontSize: 10, color: Colors.grey),
                                        ),
                                      ],
                                    ),
                              isThreeLine: true,
                            ),
                          );
                        },
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
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
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
}
