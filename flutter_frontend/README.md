# Batch Highlighter - Flutter Frontend

A professional PDF and DOCX batch highlighting application built with Flutter. This frontend connects to a backend API to process documents and highlight text based on data from CSV or Excel files.

## Features

- **Multi-platform Support**: Web, Windows, macOS, Linux, iOS, and Android
- **File Selection**: Upload CSV/Excel data files and PDF/DOCX documents
- **Column Selection**: Choose which columns contain values to search for
- **Color Selection**: Multiple highlight colors (Yellow, Green, Cyan, Pink, Blue, Red)
- **Progress Monitoring**: Real-time progress tracking with polling
- **Process Control**: Start, pause, resume, and stop processing
- **Download Results**: Download highlighted documents and logs
- **Server Failover**: Automatic fallback to backup servers
- **Responsive Design**: Optimized for desktop and mobile layouts

## Getting Started

### Prerequisites

- Flutter SDK 3.8.1 or higher
- Dart SDK
- Backend API server running

### Installation

1. Clone the repository
2. Navigate to the flutter_frontend directory
3. Install dependencies:
   ```bash
   flutter pub get
   ```

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration:
   ```env
   BASE_URLS=http://127.0.0.1:8000,https://your-backup-server.com
   API_VERSION=v1
   ENVIRONMENT=DEV
   ```

### Running the App

#### Development
```bash
# Web
flutter run -d chrome

# Windows
flutter run -d windows

# macOS
flutter run -d macos

# Linux
flutter run -d linux

# Mobile (requires connected device or emulator)
flutter run
```

#### Production Build

```bash
# Web
flutter build web --release

# Windows
flutter build windows --release

# macOS
flutter build macos --release

# Linux
flutter build linux --release

# Android
flutter build apk --release
flutter build appbundle --release

# iOS (requires macOS and Xcode)
flutter build ios --release
```

## Project Structure

```
lib/
├── main.dart                    # Application entry point
├── config/
│   └── app_config.dart          # Environment configuration
├── providers/
│   └── highlighter_provider.dart # State management
├── screens/
│   ├── file_selection_screen.dart # Step 1: File selection
│   ├── configuration_screen.dart  # Step 2: Configuration
│   ├── progress_screen.dart       # Step 3: Processing
│   └── logs_screen.dart           # Detailed logs view
└── utils/
    ├── download_helper.dart       # Download abstraction
    ├── download_helper_io.dart    # Native download implementation
    ├── download_helper_web.dart   # Web download implementation
    └── error_handler.dart         # Error handling utilities
```

## Architecture

### State Management
The app uses Provider for state management with a single `HighlighterProvider` that manages:
- File selections (data file and documents)
- Column selections
- Processing state and progress
- Server configuration and failover

### API Communication
- HTTP multipart requests for file uploads
- Polling-based progress tracking
- Automatic server failover on connection errors
- Timeout handling for all requests

### Platform Support
- **Web**: Uses `dart:js_interop` for browser downloads
- **Native**: Uses `path_provider` for file system access
- Conditional imports handle platform differences

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URLS` | Comma-separated API server URLs | `http://127.0.0.1:8000` |
| `API_VERSION` | API version prefix | `v1` |
| `API_KEY` | Optional API authentication key | - |
| `API_SECRET` | Optional API authentication secret | - |
| `ENVIRONMENT` | Environment identifier (DEV/PROD/STAGING) | `DEV` |

## Security Considerations

- File size limits (50 MB per file)
- File extension validation
- Filename sanitization before saving
- Path traversal protection
- No sensitive data in logs

## Testing

```bash
# Run unit tests
flutter test

# Run integration tests
flutter test integration_test/

# Analyze code
flutter analyze

# Check code formatting
flutter format --set-exit-if-changed .
```

## Building for Production

### Web
```bash
flutter build web --release --dart-define=ENVIRONMENT=PROD
```

### Desktop (Windows/macOS/Linux)
```bash
flutter build <platform> --release
```

### Mobile
```bash
# Android APK
flutter build apk --release

# Android App Bundle
flutter build appbundle --release

# iOS
flutter build ios --release
```

## Troubleshooting

### Common Issues

1. **CORS errors on web**: Ensure the backend has CORS enabled for your domain
2. **File picker not working**: Check platform-specific permissions
3. **Downloads failing**: Verify the backend download endpoint is accessible
4. **Server unreachable**: Check BASE_URLS configuration and network connectivity

### Debug Mode
Run with verbose logging:
```bash
flutter run --verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and analysis
5. Submit a pull request

## License

This project is proprietary software. All rights reserved.

## Support

For support, please contact the development team or file an issue in the project repository.
