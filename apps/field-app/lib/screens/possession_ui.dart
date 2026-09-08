import 'package:flutter/material.dart';

import '../theme/railos_tokens.dart';
import '../theme/railos_widgets.dart';

String prettyRailName(String value) {
  final words = value
      .replaceAll('_', ' ')
      .replaceAll('-', ' ')
      .toLowerCase()
      .split(' ')
      .where((word) => word.isNotEmpty)
      .map((word) => '${word[0].toUpperCase()}${word.substring(1)}');
  return words.join(' ');
}

RailOSStatus possessionStatusFor(String state) {
  switch (state.toUpperCase()) {
    case 'LIVE':
    case 'PROTECTED':
    case 'FIT_CERTIFIED':
      return RailOSStatus.ok;
    case 'OVERRUNNING':
      return RailOSStatus.critical;
    case 'DEFERRED':
    case 'CLEARANCE_REQUESTED':
    case 'HANDBACK_REQUESTED':
    case 'TESTING':
      return RailOSStatus.caution;
    case 'CANCELLED':
    case 'ABANDONED':
      return RailOSStatus.blocked;
    case 'SANCTIONED':
    case 'ISOLATION_IN_PROGRESS':
      return RailOSStatus.info;
    case 'CLEARED':
      return RailOSStatus.ok;
    default:
      return RailOSStatus.unknown;
  }
}

String possessionActionLabel(String action) {
  const labels = <String, String>{
    'request-clearance': 'Request clearance',
    'grant-clearance': 'Grant clearance',
    'defer': 'Defer block',
    'start-isolation': 'Start isolation',
    'issue-t351': 'Issue T/351',
    'endorse-t351': 'Endorse T/351',
    'confirm-earthing': 'Confirm earthing',
    'issue-ptw': 'Issue PTW',
    'plant-protection': 'Plant protection',
    'start-work': 'Start work',
    'declare-overrun': 'Declare overrun',
    'start-testing': 'Start testing',
    'record-correspondence-test': 'Record correspondence test',
    'request-handback': 'Request handback',
    'remove-discharge-rods': 'Discharge rods removed',
    'cancel-ptw': 'Cancel PTW',
    're-energise': 'Re-energise',
    'certify-fitness': 'Certify fitness',
    'station-close': 'Station close',
    'close': 'Close possession',
    'cancel': 'Cancel possession',
    'abandon': 'Abandon possession',
  };
  return labels[action] ?? prettyRailName(action);
}

IconData possessionActionIcon(String action) {
  switch (action) {
    case 'request-clearance':
      return Icons.outgoing_mail;
    case 'grant-clearance':
      return Icons.verified_outlined;
    case 'defer':
      return Icons.schedule_outlined;
    case 'issue-t351':
    case 'endorse-t351':
      return Icons.description_outlined;
    case 'issue-ptw':
    case 'cancel-ptw':
      return Icons.power_outlined;
    case 'confirm-earthing':
      return Icons.electrical_services_outlined;
    case 'plant-protection':
      return Icons.shield_outlined;
    case 'start-work':
      return Icons.play_arrow_outlined;
    case 'declare-overrun':
      return Icons.timer_outlined;
    case 'record-correspondence-test':
      return Icons.fact_check_outlined;
    case 'request-handback':
      return Icons.assignment_return_outlined;
    case 'remove-discharge-rods':
      return Icons.remove_circle_outline;
    case 'certify-fitness':
      return Icons.health_and_safety_outlined;
    case 'close':
    case 'station-close':
      return Icons.lock_outline;
    case 'cancel':
    case 'abandon':
      return Icons.block_outlined;
    default:
      return Icons.arrow_forward_outlined;
  }
}

String formatUtcForField(dynamic value) {
  if (value == null || value.toString().isEmpty) return 'Not recorded';
  final parsed = DateTime.tryParse(value.toString());
  if (parsed == null) return value.toString();
  final utc = parsed.toUtc();
  String two(int item) => item.toString().padLeft(2, '0');
  return '${utc.year}-${two(utc.month)}-${two(utc.day)} ${two(utc.hour)}:${two(utc.minute)} UTC';
}

String countdownLabel(String? iso, DateTime now) {
  if (iso == null) return 'Time not provided';
  final target = DateTime.tryParse(iso)?.toUtc();
  if (target == null) return 'Time not provided';
  final difference = target.difference(now.toUtc());
  final minutes = difference.inMinutes.abs();
  final hours = minutes ~/ 60;
  final remaining = minutes % 60;
  final duration = hours > 0 ? '${hours}h ${remaining}m' : '${remaining}m';
  return difference.isNegative ? 'Ended $duration ago' : 'In $duration';
}

class RailOSPossessionActionButton extends StatelessWidget {
  final String action;
  final VoidCallback? onPressed;
  final bool isLoading;

  const RailOSPossessionActionButton({
    super.key,
    required this.action,
    required this.onPressed,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    final label = possessionActionLabel(action);
    return SizedBox(
      width: double.infinity,
      height: RailOSTokens.minTouchTargetDp,
      child: ElevatedButton.icon(
        onPressed: isLoading ? null : onPressed,
        icon: isLoading
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: RailOSTokens.bg_canvas,
                ),
              )
            : Icon(possessionActionIcon(action), size: 18),
        label: Text(label),
      ),
    );
  }
}

class RailOSPanel extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const RailOSPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(RailOSTokens.spacingMd),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: padding,
      decoration: BoxDecoration(
        color: RailOSTokens.bg_panel,
        borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
        border: Border.all(color: RailOSTokens.border_default),
      ),
      child: child,
    );
  }
}

Widget buildRuleLabel(BuildContext context, String rule) {
  return Text(
    'Rule: $rule',
    style: Theme.of(context).textTheme.bodySmall?.copyWith(
      fontFamily: 'monospace',
      color: RailOSTokens.text_muted,
    ),
  );
}
