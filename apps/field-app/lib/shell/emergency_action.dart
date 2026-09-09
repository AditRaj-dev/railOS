import 'package:flutter/material.dart';

import '../screens/emergency_screen.dart';
import '../services/api_client.dart';
import '../theme/railos_tokens.dart';

/// Persistent emergency hazard action displayed on the AppBar across all field screens.
/// Guarantees that the emergency button is reachable from every operational screen,
/// including on-track execution (Work, Handback, Isolation, TaskDetail).
class EmergencyAppBarAction extends StatelessWidget {
  final RailOSApiClient apiClient;

  const EmergencyAppBarAction({
    super.key,
    required this.apiClient,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Emergency Hazard Dispatch',
      child: IconButton(
        icon: const Icon(
          Icons.warning_amber_rounded,
          color: RailOSTokens.status_critical_fg,
          size: 22,
        ),
        tooltip: 'Emergency Hazard Report',
        style: IconButton.styleFrom(
          backgroundColor: RailOSTokens.status_critical_bg,
          side: const BorderSide(
            color: RailOSTokens.status_critical_border,
            width: 1,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
          ),
        ),
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => EmergencyScreen(apiClient: apiClient),
              settings: const RouteSettings(name: '/emergency'),
            ),
          );
        },
      ),
    );
  }
}
