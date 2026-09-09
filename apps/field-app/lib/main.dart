import 'package:flutter/material.dart';
import 'screens/emergency_screen.dart';
import 'screens/handback_screen.dart';
import 'screens/isolation_screen.dart';
import 'screens/login_screen.dart';
import 'screens/possession_screen.dart';
import 'screens/work_screen.dart';
import 'services/api_client.dart';
import 'shell/field_shell.dart';
import 'storage/offline_evidence_queue.dart';
import 'theme/railos_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Restore the session/cache before the first frame so a valid 24-hour
  // entitlement can open directly into the field surface after a restart.
  await OfflineEvidenceQueue().initialize();
  runApp(const RailOSFieldApp());
}

class RailOSFieldApp extends StatefulWidget {
  const RailOSFieldApp({super.key});

  @override
  State<RailOSFieldApp> createState() => _RailOSFieldAppState();
}

class _RailOSFieldAppState extends State<RailOSFieldApp> {
  final _apiClient = RailOSApiClient();
  final _queue = OfflineEvidenceQueue();
  bool _isLoggedIn = false;

  @override
  void initState() {
    super.initState();
    _isLoggedIn = _queue.currentSession?.isOfflineEntitlementValid ?? false;
    _queue.addListener(_handleSessionChange);
  }

  @override
  void dispose() {
    _queue.removeListener(_handleSessionChange);
    super.dispose();
  }

  void _handleSessionChange() {
    final hasValidSession =
        _queue.currentSession?.isOfflineEntitlementValid ?? false;
    if (hasValidSession != _isLoggedIn) {
      setState(() => _isLoggedIn = hasValidSession);
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Railblock Field Operations',
      debugShowCheckedModeBanner: false,
      theme: RailOSTheme.darkTheme,
      home: _isLoggedIn
          ? FieldShell(
              apiClient: _apiClient,
              onLogout: () {
                _queue.clearSession();
                setState(() => _isLoggedIn = false);
              },
            )
          : LoginScreen(
              apiClient: _apiClient,
              onLoginSuccess: () {
                setState(() => _isLoggedIn = true);
              },
            ),
      onGenerateRoute: (settings) {
        final uri = Uri.parse(settings.name ?? '/');
        final args = settings.arguments;

        switch (uri.path) {
          case '/emergency':
            return MaterialPageRoute(
              builder: (_) => EmergencyScreen(apiClient: _apiClient),
              settings: settings,
            );
          case '/possession':
            if (args is Map<String, dynamic>) {
              return MaterialPageRoute(
                builder: (_) => PossessionScreen(
                  possession: args,
                  apiClient: _apiClient,
                ),
                settings: settings,
              );
            }
            break;
          case '/isolation':
            if (args is Map<String, dynamic>) {
              return MaterialPageRoute(
                builder: (_) => IsolationScreen(
                  possession: args,
                  apiClient: _apiClient,
                ),
                settings: settings,
              );
            }
            break;
          case '/work':
            if (args is Map<String, dynamic>) {
              return MaterialPageRoute(
                builder: (_) => WorkScreen(
                  task: args['task'] as Map<String, dynamic>? ?? const {},
                  possession: args['possession'] as Map<String, dynamic>? ?? const {},
                  apiClient: _apiClient,
                ),
                settings: settings,
              );
            }
            break;
          case '/handback':
            if (args is Map<String, dynamic>) {
              return MaterialPageRoute(
                builder: (_) => HandbackScreen(
                  possession: args,
                  apiClient: _apiClient,
                ),
                settings: settings,
              );
            }
            break;
        }
        return null;
      },
    );
  }
}
