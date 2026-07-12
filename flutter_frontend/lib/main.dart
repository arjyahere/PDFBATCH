import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'providers/highlighter_provider.dart';
import 'screens/file_selection_screen.dart';
import 'screens/configuration_screen.dart';
import 'screens/progress_screen.dart';
import 'screens/logs_screen.dart';

/// Application entry point
/// 
/// Initializes the Flutter binding, loads environment configuration,
/// and launches the Batch Highlighter application.
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Load .env file with error handling
  try {
    await dotenv.load(fileName: '.env');
  } catch (e) {
    debugPrint('Warning: Could not load .env file: $e');
  }

  runApp(const BatchHighlighterApp());
}

/// Root widget of the Batch Highlighter application
/// 
/// Provides the app theme configuration, routing, and state management
/// through Provider pattern.
class BatchHighlighterApp extends StatelessWidget {
  const BatchHighlighterApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (context) => HighlighterProvider(),
      child: MaterialApp(
        title: 'Batch Highlighter',
        debugShowCheckedModeBanner: false,
        theme: _buildLightTheme(),
        darkTheme: _buildDarkTheme(),
        themeMode: ThemeMode.system,
        home: const HomePage(),
        routes: {
          '/logs': (context) => const LogsScreen(),
        },
      ),
    );
  }

  /// Builds the light theme configuration
  ThemeData _buildLightTheme() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: Colors.blue,
        brightness: Brightness.light,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 2,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }

  /// Builds the dark theme configuration
  ThemeData _buildDarkTheme() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: Colors.blue,
        brightness: Brightness.dark,
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: true,
        elevation: 2,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }
}

/// Main home page with step-based navigation
/// 
/// Supports both desktop (tab-based) and mobile (stepper-based) layouts.
/// Manages the three-step workflow: File Selection, Configuration, and Processing.
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentStep = 0;

  /// List of screen widgets for each step
  final List<Widget> _screens = const [
    FileSelectionScreen(),
    ConfigurationScreen(),
    ProgressScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final isDesktop = MediaQuery.of(context).size.width > 768;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Batch Highlighter'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Reset',
            onPressed: () {
              context.read<HighlighterProvider>().reset();
              setState(() => _currentStep = 0);
            },
          ),
        ],
      ),
      body: Consumer<HighlighterProvider>(
        builder: (context, provider, child) {
          if (isDesktop) {
            return _buildDesktopLayout(provider);
          } else {
            return _buildMobileLayout();
          }
        },
      ),
    );
  }

  /// Builds the desktop layout with tab-based navigation
  Widget _buildDesktopLayout(HighlighterProvider provider) {
    return Column(
      children: [
        ColoredBox(
          color: Theme.of(context).colorScheme.surface,
          child: Row(
            children: [
              _buildStepTab(0, 'Select Files', provider),
              _buildStepTab(1, 'Configure', provider),
              _buildStepTab(2, 'Process & Download', provider),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: _getCurrentScreen(),
          ),
        ),
      ],
    );
  }

  /// Builds the mobile layout with Stepper navigation
  Widget _buildMobileLayout() {
    return Stepper(
      currentStep: _currentStep,
      onStepTapped: (step) {
        setState(() => _currentStep = step);
      },
      onStepContinue: () {
        if (_currentStep < _screens.length - 1) {
          setState(() => _currentStep++);
        }
      },
      onStepCancel: () {
        if (_currentStep > 0) {
          setState(() => _currentStep--);
        }
      },
      steps: [
        Step(
          title: const Text('Select Files'),
          subtitle: const Text('Choose data file and documents'),
          content: const FileSelectionScreen(),
          isActive: _currentStep >= 0,
          state: _currentStep > 0
              ? StepState.complete
              : (_currentStep == 0 ? StepState.editing : StepState.indexed),
        ),
        Step(
          title: const Text('Configure'),
          subtitle: const Text('Select color and columns'),
          content: const ConfigurationScreen(),
          isActive: _currentStep >= 1,
          state: _currentStep > 1
              ? StepState.complete
              : (_currentStep == 1
                  ? StepState.editing
                  : StepState.indexed),
        ),
        Step(
          title: const Text('Process & Download'),
          subtitle: const Text('Start processing and download results'),
          content: const ProgressScreen(),
          isActive: _currentStep >= 2,
          state: _currentStep == 2
              ? StepState.editing
              : StepState.indexed,
        ),
      ],
      controlsBuilder: (context, details) {
        return Padding(
          padding: const EdgeInsets.only(top: 16.0),
          child: Row(
            children: [
              if (_currentStep > 0)
                TextButton(
                  onPressed: details.onStepCancel,
                  child: const Text('Back'),
                ),
              const SizedBox(width: 8),
              if (_currentStep < _screens.length - 1)
                ElevatedButton(
                  onPressed: details.onStepContinue,
                  child: const Text('Next'),
                ),
            ],
          ),
        );
      },
    );
  }

  /// Builds a tab for desktop navigation
  Widget _buildStepTab(int stepIndex, String title, HighlighterProvider provider) {
    final isActive = _currentStep == stepIndex;
    final isCompleted = _isStepCompleted(stepIndex, provider);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _currentStep = stepIndex),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: isActive ? colorScheme.primary : Colors.transparent,
                width: 3,
              ),
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (isCompleted)
                Icon(Icons.check_circle, size: 20, color: colorScheme.primary)
              else
                CircleAvatar(
                  radius: 10,
                  backgroundColor: isActive
                      ? colorScheme.primary
                      : Colors.grey,
                  child: Text(
                    '${stepIndex + 1}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              const SizedBox(width: 8),
              Text(
                title,
                style: TextStyle(
                  fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                  color: isActive ? colorScheme.primary : null,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Checks if a specific step is completed based on provider state
  bool _isStepCompleted(int stepIndex, HighlighterProvider provider) {
    switch (stepIndex) {
      case 0:
        return provider.dataFile != null &&
            provider.documentFiles.isNotEmpty &&
            provider.columns.isNotEmpty;
      case 1:
        return provider.selectedColumns.isNotEmpty;
      case 2:
        return provider.progress >= 100;
      default:
        return false;
    }
  }

  /// Returns the current screen widget based on the active step
  Widget _getCurrentScreen() {
    switch (_currentStep) {
      case 0:
        return FileSelectionScreen(
          onNext: () => setState(() => _currentStep = 1),
        );
      case 1:
        return ConfigurationScreen(
          onBack: () => setState(() => _currentStep = 0),
          onNext: () => setState(() => _currentStep = 2),
        );
      case 2:
        return ProgressScreen(
          onBack: () => setState(() => _currentStep = 1),
          onViewLogs: () => Navigator.of(context).pushNamed('/logs'),
        );
      default:
        return FileSelectionScreen(
          onNext: () => setState(() => _currentStep = 1),
        );
    }
  }
}

/// Extension to add safe navigation methods to BuildContext
extension SafeNavigation on BuildContext {
  /// Safely navigate only if the context is still mounted
  void safeNavigate(VoidCallback navigation) {
    if (mounted) {
      navigation();
    }
  }
}
