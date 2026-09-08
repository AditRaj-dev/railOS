import 'package:flutter/material.dart';
import 'railos_tokens.dart';

enum RailOSStatus {
  ok,
  info,
  caution,
  warning,
  critical,
  blocked,
  unknown,
}

/// Status badge / chip with paired icon + label complying with WCAG AA redundancy
class RailOSStatusChip extends StatelessWidget {
  final String label;
  final RailOSStatus status;
  final IconData? customIcon;
  final bool compact;

  const RailOSStatusChip({
    super.key,
    required this.label,
    required this.status,
    this.customIcon,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color fg;
    Color text;
    IconData icon;

    switch (status) {
      case RailOSStatus.ok:
        bg = RailOSTokens.status_ok_bg;
        border = RailOSTokens.status_ok_border;
        fg = RailOSTokens.status_ok_fg;
        text = RailOSTokens.status_ok_text;
        icon = customIcon ?? Icons.check_circle_outline;
        break;
      case RailOSStatus.info:
        bg = RailOSTokens.status_info_bg;
        border = RailOSTokens.status_info_border;
        fg = RailOSTokens.status_info_fg;
        text = RailOSTokens.status_info_text;
        icon = customIcon ?? Icons.info_outline;
        break;
      case RailOSStatus.caution:
        bg = RailOSTokens.status_caution_bg;
        border = RailOSTokens.status_caution_border;
        fg = RailOSTokens.status_caution_fg;
        text = RailOSTokens.status_caution_text;
        icon = customIcon ?? Icons.warning_amber_rounded;
        break;
      case RailOSStatus.warning:
        bg = RailOSTokens.status_warning_bg;
        border = RailOSTokens.status_warning_border;
        fg = RailOSTokens.status_warning_fg;
        text = RailOSTokens.status_warning_text;
        icon = customIcon ?? Icons.report_problem_outlined;
        break;
      case RailOSStatus.critical:
        bg = RailOSTokens.status_critical_bg;
        border = RailOSTokens.status_critical_border;
        fg = RailOSTokens.status_critical_fg;
        text = RailOSTokens.status_critical_text;
        icon = customIcon ?? Icons.error_outline;
        break;
      case RailOSStatus.blocked:
        bg = RailOSTokens.status_blocked_bg;
        border = RailOSTokens.status_blocked_border;
        fg = RailOSTokens.status_blocked_fg;
        text = RailOSTokens.status_blocked_text;
        icon = customIcon ?? Icons.block;
        break;
      case RailOSStatus.unknown:
        bg = RailOSTokens.status_unknown_bg;
        border = RailOSTokens.status_unknown_border;
        fg = RailOSTokens.status_unknown_fg;
        text = RailOSTokens.status_unknown_text;
        icon = customIcon ?? Icons.help_outline;
        break;
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 6 : 8,
        vertical: compact ? 2 : 4,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
        border: Border.all(color: border, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: compact ? 12 : 14, color: fg),
          SizedBox(width: compact ? 4 : 6),
          Text(
            label,
            style: TextStyle(
              color: text,
              fontSize: compact ? 11 : 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }
}

/// Department identity badge matching Next.js control center DepartmentBadge
class RailOSDepartmentBadge extends StatelessWidget {
  final String department;

  const RailOSDepartmentBadge({
    super.key,
    required this.department,
  });

  @override
  Widget build(BuildContext context) {
    final deptUpper = department.toUpperCase();
    Color bg;
    Color border;
    Color text;
    String displayLabel;

    if (deptUpper.contains('SNT') || deptUpper.contains('SIGNAL') || deptUpper.contains('S_AND_T')) {
      bg = RailOSTokens.dept_snt_bg;
      border = RailOSTokens.dept_snt_border;
      text = RailOSTokens.dept_snt_text;
      displayLabel = 'S&T / SIGNAL';
    } else if (deptUpper.contains('TRD') || deptUpper.contains('TRACTION') || deptUpper.contains('OHE')) {
      bg = RailOSTokens.dept_trd_bg;
      border = RailOSTokens.dept_trd_border;
      text = RailOSTokens.dept_trd_text;
      displayLabel = 'TRD / OHE';
    } else if (deptUpper.contains('OPERAT')) {
      bg = RailOSTokens.status_unknown_bg;
      border = RailOSTokens.status_unknown_border;
      text = RailOSTokens.status_unknown_text;
      displayLabel = 'OPERATIONS';
    } else {
      // Default to Engineering / Track (ENGG / CIVIL)
      bg = RailOSTokens.dept_engg_bg;
      border = RailOSTokens.dept_engg_border;
      text = RailOSTokens.dept_engg_text;
      displayLabel = 'ENG / TRACK';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
        border: Border.all(color: border, width: 1),
      ),
      child: Text(
        displayLabel,
        style: TextStyle(
          color: text,
          fontSize: 10,
          fontFamily: 'monospace',
          fontWeight: FontWeight.bold,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

/// Telemetry Pill for GPS / Freshness / Status Indicators
class RailOSPill extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color bg;
  final Color border;
  final Color fg;
  final Color textColor;

  const RailOSPill({
    super.key,
    required this.icon,
    required this.label,
    required this.bg,
    required this.border,
    required this.fg,
    required this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: border, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: fg),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: textColor,
              fontSize: 11,
              fontFamily: 'monospace',
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
