import 'package:flutter/material.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_client.dart';
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
      title: 'RailOS Field Operations',
      debugShowCheckedModeBanner: false,
      theme: RailOSTheme.darkTheme,
      home: _isLoggedIn
          ? DashboardScreen(
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
    );
  }
}
