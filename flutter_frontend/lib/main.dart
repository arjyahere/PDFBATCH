import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'providers/highlighter_provider.dart';
import 'screens/file_selection_screen.dart';
import 'screens/configuration_screen.dart';
import 'screens/progress_screen.dart';
import 'screens/logs_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 🔥 Load your .env file BEFORE anything else
  await dotenv.load(fileName: ".env");

  runApp(const BatchHighlighterApp());
}

class BatchHighlighterApp extends StatelessWidget {
  const BatchHighlighterApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (context) => HighlighterProvider(),
      child: MaterialApp(
        title: 'Batch Highlighter',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
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
        ),
        darkTheme: ThemeData(
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
        ),
        themeMode: ThemeMode.system,
        home: const HomePage(),
        routes: {
          '/logs': (context) => const LogsScreen(),
        },
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentStep = 0;

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
            // Desktop layout with tabs - allow free navigation
            return Column(
              children: [
                Container(
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
          } else {
            // Mobile layout with Stepper - allow free navigation
            return Stepper(
              currentStep: _currentStep,
              onStepTapped: (step) {
                // Allow navigation to any step
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
                  subtitle: const Text('Select color and column'),
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
                return Row(
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
                );
              },
            );
          }
        },
      ),
    );
  }

  Widget _buildStepTab(int stepIndex, String title, HighlighterProvider provider) {
    final isActive = _currentStep == stepIndex;
    final isCompleted = _isStepCompleted(stepIndex, provider);

    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _currentStep = stepIndex),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: isActive ? Theme.of(context).colorScheme.primary : Colors.transparent,
                width: 3,
              ),
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (isCompleted)
                const Icon(Icons.check_circle, size: 20, color: Colors.green)
              else
                CircleAvatar(
                  radius: 10,
                  backgroundColor: isActive
                      ? Theme.of(context).colorScheme.primary
                      : Colors.grey,
                  child: Text(
                    '${stepIndex + 1}',
                    style: TextStyle(
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
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  bool _isStepCompleted(int stepIndex, HighlighterProvider provider) {
    switch (stepIndex) {
      case 0:
        return provider.dataFile != null && provider.documentFiles.isNotEmpty && provider.columns.isNotEmpty;
      case 1:
        return provider.selectedColumn != null;
      case 2:
        return provider.progress >= 100;
      default:
        return false;
    }
  }

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
