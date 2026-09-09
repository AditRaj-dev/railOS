import 'dart:async';

import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../shell/emergency_action.dart';
import '../theme/railos_tokens.dart';
import '../theme/railos_widgets.dart';
import 'handback_screen.dart';
import 'isolation_screen.dart';
import 'possession_ui.dart';
import 'work_screen.dart';

class PossessionScreen extends StatefulWidget {
  final Map<String, dynamic> possession;
  final RailOSApiClient apiClient;

  const PossessionScreen({
    super.key,
    required this.possession,
    required this.apiClient,
  });

  @override
  State<PossessionScreen> createState() => _PossessionScreenState();
}

class _PossessionScreenState extends State<PossessionScreen> {
  late Map<String, dynamic> _possession;
  Timer? _clock;
  DateTime _now = DateTime.now().toUtc();
  String? _actionInFlight;
  final Set<String> _queuedActions = <String>{};

  @override
  void initState() {
    super.initState();
    _possession = Map<String, dynamic>.from(widget.possession);
    _clock = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now().toUtc());
    });
  }

  @override
  void dispose() {
    _clock?.cancel();
    super.dispose();
  }

  Future<void> _runAction(String action, {String? deferredUntilUtc}) async {
    setState(() => _actionInFlight = action);
    try {
      final result = await widget.apiClient.postPossessionAction(
        possessionId: _string('possessionId'),
        action: action,
        deferredUntilUtc: deferredUntilUtc,
      );
      if (!mounted) return;
      setState(() {
        _actionInFlight = null;
        if (result['queued'] == true) {
          _queuedActions.add(action);
        } else {
          _possession = result;
        }
      });
      _announce(
        result['queued'] == true
            ? '${possessionActionLabel(action)} saved offline. It will replay when online.'
            : '${possessionActionLabel(action)} recorded.',
        result['queued'] == true
            ? RailOSTokens.status_caution_bg
            : RailOSTokens.status_ok_bg,
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _actionInFlight = null);
      _announce(_recoveryMessage(error), RailOSTokens.status_critical_bg);
    }
  }

  Future<void> _defer() async {
    final defaultTime = DateTime.now().toUtc().add(const Duration(hours: 1));
    final controller = TextEditingController(
      text: defaultTime.toIso8601String(),
    );
    final value = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Defer this block'),
        content: TextField(
          controller: controller,
          autofocus: true,
          minLines: 1,
          maxLines: 2,
          decoration: const InputDecoration(
            labelText: 'New clearance time (UTC)',
            helperText: 'Use ISO 8601, for example 2026-09-08T12:00:00Z.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Keep current time'),
          ),
          ElevatedButton(
            onPressed: () =>
                Navigator.pop(dialogContext, controller.text.trim()),
            child: const Text('Save new time'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (!mounted || value == null || value.isEmpty) return;
    if (DateTime.tryParse(value) == null) {
      _announce(
        'That time is not valid. Enter an ISO 8601 UTC time.',
        RailOSTokens.status_critical_bg,
      );
      return;
    }
    await _runAction(
      'defer',
      deferredUntilUtc: DateTime.parse(value).toUtc().toIso8601String(),
    );
  }

  void _announce(String message, Color background) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: background,
          duration: const Duration(seconds: 4),
        ),
      );
  }

  String _string(String key, [String fallback = '']) =>
      _possession[key]?.toString() ?? fallback;

  List<String> get _allowedActions =>
      (_possession['allowedActions'] as List? ?? const [])
          .map((value) => value.toString())
          .toList();

  Map<String, dynamic>? get _firstTask {
    final ids = (_possession['assignedTaskIds'] as List? ?? const [])
        .map((value) => value.toString())
        .toSet();
    for (final task in widget.apiClient.queue.cachedTasks) {
      if (ids.contains(task['taskId'])) return task;
    }
    if (ids.isEmpty && widget.apiClient.queue.cachedTasks.isNotEmpty) {
      return widget.apiClient.queue.cachedTasks.first;
    }
    return null;
  }

  Widget _windowRow({
    required String label,
    required String value,
    required String countdown,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: RailOSTokens.spacingSm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 88,
            child: Text(label, style: Theme.of(context).textTheme.bodySmall),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(fontFamily: 'monospace'),
                ),
                Text(countdown, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _workflowLink({
    required String label,
    required IconData icon,
    required VoidCallback onPressed,
  }) {
    return SizedBox(
      width: double.infinity,
      height: RailOSTokens.minTouchTargetDp,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
      ),
    );
  }

  Future<void> _openIsolation() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => IsolationScreen(
          possession: _possession,
          apiClient: widget.apiClient,
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  Future<void> _openHandback() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => HandbackScreen(
          possession: _possession,
          apiClient: widget.apiClient,
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  Future<void> _openWork() async {
    final task =
        _firstTask ??
        <String, dynamic>{
          'taskId': _string('blockId', 'Block work'),
          'title': 'Possession work',
          'department': _string('department', 'ENGG'),
          'steps': const <Map<String, dynamic>>[],
        };
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => WorkScreen(
          task: task,
          possession: _possession,
          apiClient: widget.apiClient,
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  String _recoveryMessage(Object error) {
    if (error is RailOSApiException) {
      final allowed = error.details['allowedActions'];
      if (allowed is List && allowed.isNotEmpty) {
        return '${error.message} Available actions: ${allowed.join(', ')}.';
      }
      return '${error.message} Check the latest possession state and try again.';
    }
    return error.toString().replaceFirst('Exception: ', '');
  }

  @override
  Widget build(BuildContext context) {
    final state = _string('state', 'UNKNOWN');
    final id = _string('possessionId', 'Possession');
    final plannedStart = _possession['plannedStartUtc'] as String?;
    final plannedEnd = _possession['plannedEndUtc'] as String?;
    final isDeferred = state == 'DEFERRED';
    final task = _firstTask;
    final stateLabel = prettyRailName(state);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          id,
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontFamily: 'monospace'),
        ),
        actions: [
          EmergencyAppBarAction(apiClient: widget.apiClient),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            try {
              final updated = await widget.apiClient.fetchPossession(id);
              if (mounted) setState(() => _possession = updated);
            } catch (e) {
              if (mounted) {
                _announce(
                  'Failed to refresh possession: ${_recoveryMessage(e)}',
                  RailOSTokens.status_critical_bg,
                );
              }
            }
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(RailOSTokens.spacingMd),
            children: [
              Semantics(
                header: true,
                child: Text(
                  'Possession authority',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              const SizedBox(height: RailOSTokens.spacingSm),
              RailOSPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: RailOSTokens.spacingSm,
                      runSpacing: RailOSTokens.spacingSm,
                      children: [
                        RailOSStatusChip(
                          label: stateLabel,
                          status: possessionStatusFor(state),
                        ),
                        RailOSDepartmentBadge(
                          department: _string('department', 'ENGG'),
                        ),
                        if (_possession['synthetic'] == true)
                          const RailOSPill(
                            icon: Icons.science_outlined,
                            label: 'Synthetic demo',
                            bg: RailOSTokens.status_info_bg,
                            border: RailOSTokens.status_info_border,
                            fg: RailOSTokens.status_info_fg,
                            textColor: RailOSTokens.status_info_text,
                          ),
                      ],
                    ),
                    const SizedBox(height: RailOSTokens.spacingMd),
                    Text(
                      '${_string('sectionId', 'Section not provided')} • Track ${_string('track', 'not provided')}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: RailOSTokens.spacingSm),
                    Text(
                      'Block ${_string('blockId', 'not provided')}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: RailOSTokens.spacingMd),
              RailOSPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Planned window',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: RailOSTokens.spacingMd),
                    _windowRow(
                      label: 'Starts',
                      value: formatUtcForField(plannedStart),
                      countdown: countdownLabel(plannedStart, _now),
                    ),
                    _windowRow(
                      label: 'Ends',
                      value: formatUtcForField(plannedEnd),
                      countdown: countdownLabel(plannedEnd, _now),
                    ),
                    if (isDeferred) ...[
                      const Divider(height: RailOSTokens.spacingLg),
                      RailOSStatusChip(
                        label:
                            'New clearance: ${formatUtcForField(_possession['deferredUntilUtc'])}',
                        status: RailOSStatus.caution,
                        customIcon: Icons.schedule_outlined,
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: RailOSTokens.spacingMd),
              if (_queuedActions.isNotEmpty) ...[
                Semantics(
                  liveRegion: true,
                  child: RailOSPanel(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.cloud_off_outlined,
                          color: RailOSTokens.status_caution_fg,
                        ),
                        const SizedBox(width: RailOSTokens.spacingSm),
                        Expanded(
                          child: Text(
                            'Offline action saved: ${_queuedActions.map(possessionActionLabel).join(', ')}. It will replay when the connection returns.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: RailOSTokens.spacingMd),
              ],
              Text(
                'Available actions',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: RailOSTokens.spacingSm),
              if (_allowedActions.isEmpty)
                RailOSPanel(
                  child: Text(
                    'No action is available for your role in this state. Refresh after the next authority handoff.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                )
              else
                ..._allowedActions.map((action) {
                  final inFlight = _actionInFlight == action;
                  final anyInFlight = _actionInFlight != null;
                  if (action == 'defer') {
                    return Padding(
                      padding: const EdgeInsets.only(
                        bottom: RailOSTokens.spacingSm,
                      ),
                      child: RailOSPossessionActionButton(
                        action: action,
                        onPressed: anyInFlight ? null : _defer,
                        isLoading: inFlight,
                      ),
                    );
                  }
                  return Padding(
                    padding: const EdgeInsets.only(
                      bottom: RailOSTokens.spacingSm,
                    ),
                    child: RailOSPossessionActionButton(
                      action: action,
                      onPressed: anyInFlight ? null : () => _runAction(action),
                      isLoading: inFlight,
                    ),
                  );
                }),
              const SizedBox(height: RailOSTokens.spacingSm),
              Text(
                'Related workflows',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: RailOSTokens.spacingSm),
              if (state == 'SANCTIONED' ||
                  state == 'CLEARANCE_REQUESTED' ||
                  state == 'DEFERRED' ||
                  state == 'ISOLATION_IN_PROGRESS')
                Padding(
                  padding: const EdgeInsets.only(
                    bottom: RailOSTokens.spacingSm,
                  ),
                  child: _workflowLink(
                    label: 'Open isolation & protection',
                    icon: Icons.electrical_services_outlined,
                    onPressed: _openIsolation,
                  ),
                ),
              if (task != null ||
                  state == 'PROTECTED' ||
                  state == 'LIVE' ||
                  state == 'OVERRUNNING')
                Padding(
                  padding: const EdgeInsets.only(
                    bottom: RailOSTokens.spacingSm,
                  ),
                  child: _workflowLink(
                    label: 'Open work progression',
                    icon: Icons.engineering_outlined,
                    onPressed: _openWork,
                  ),
                ),
              if (state == 'TESTING' ||
                  state == 'HANDBACK_REQUESTED' ||
                  state == 'FIT_CERTIFIED')
                _workflowLink(
                  label: 'Open testing & handback',
                  icon: Icons.assignment_return_outlined,
                  onPressed: _openHandback,
                ),
              if (_possession['transitions'] is List &&
                  (_possession['transitions'] as List).isNotEmpty) ...[
                const SizedBox(height: RailOSTokens.spacingMd),
                RailOSPanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Latest authority record',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: RailOSTokens.spacingSm),
                      Builder(
                        builder: (_) {
                          final rows = _possession['transitions'] as List;
                          final latest = rows.last is Map
                              ? Map<String, dynamic>.from(rows.last as Map)
                              : <String, dynamic>{};
                          return Text(
                            '${prettyRailName(latest['action']?.toString() ?? 'transition')} • ${latest['role'] ?? 'role not recorded'}\n${formatUtcForField(latest['occurredAtUtc'])}\nRule: ${latest['ruleCitation'] ?? 'not provided'}',
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(fontFamily: 'monospace'),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
