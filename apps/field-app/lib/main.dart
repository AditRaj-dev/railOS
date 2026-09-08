import 'package:flutter/material.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_client.dart';
import 'storage/offline_evidence_queue.dart';
import 'theme/railos_tokens.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
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
    _queue.addListener(_handleSessionChange);
  }

  @override
  void dispose() {
    _queue.removeListener(_handleSessionChange);
    super.dispose();
  }

  void _handleSessionChange() {
    final hasValidSession = _queue.currentSession?.isOfflineEntitlementValid ?? false;
    if (hasValidSession != _isLoggedIn) {
      setState(() => _isLoggedIn = hasValidSession);
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RailOS Field Evidence',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: RailOSTokens.bg_darkRoot,
        primaryColor: RailOSTokens.primary_railBlue,
        colorScheme: const ColorScheme.dark(
          primary: RailOSTokens.primary_railBlue,
          secondary: Colors.cyanAccent,
          surface: RailOSTokens.bg_darkSurface,
          error: RailOSTokens.primary_safetyRed,
        ),
        fontFamily: 'sans-serif',
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            minimumSize: const Size.fromHeight(RailOSTokens.minTouchTargetDp),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
            ),
          ),
        ),
      ),
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
