import 'dart:async';

import 'package:flutter/material.dart';

import '../models/evidence_models.dart';
import '../services/api_client.dart';
import '../theme/railos_tokens.dart';
import '../theme/railos_widgets.dart';
import 'possession_ui.dart';
import 'task_detail_screen.dart';

class WorkScreen extends StatefulWidget {
  final Map<String, dynamic> task;
  final Map<String, dynamic> possession;
  final RailOSApiClient apiClient;

  const WorkScreen({
    super.key,
    required this.task,
    required this.possession,
    required this.apiClient,
  });

  @override
  State<WorkScreen> createState() => _WorkScreenState();
}

class _WorkScreenState extends State<WorkScreen> {
  late WorkExecutionStatus _status;
  late Map<String, dynamic> _possession;
  late List<WorkStep> _steps;
  Timer? _clock;
  DateTime _now = DateTime.now().toUtc();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _possession = Map<String, dynamic>.from(widget.possession);
    _steps = (widget.task['steps'] as List? ?? const [])
        .whereType<Map>()
        .map((step) => WorkStep.fromJson(Map<String, dynamic>.from(step)))
        .toList();
    _status =
        _parseStatus(widget.task['executionStatus']?.toString()) ??
        (_steps.any((step) => step.status != WorkExecutionStatus.ready)
            ? WorkExecutionStatus.inProgress
            : WorkExecutionStatus.ready);
    _clock = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now().toUtc());
    });
  }

  @override
  void dispose() {
    _clock?.cancel();
    super.dispose();
  }

  WorkExecutionStatus? _parseStatus(String? value) {
    if (value == null) return null;
    final normalized = value.toUpperCase();
    for (final status in WorkExecutionStatus.values) {
      if (status.name.toUpperCase() == normalized) return status;
    }
    return null;
  }

  String get _taskId => widget.task['taskId']?.toString() ?? 'WORK';
  String get _possessionId => _possession['possessionId']?.toString() ?? '';

  List<String> get _allowedActions =>
      (_possession['allowedActions'] as List? ?? const [])
          .map((value) => value.toString())
          .toList();

  DateTime? get _plannedEnd {
    final value = _possession['plannedEndUtc'];
    return value is String ? DateTime.tryParse(value)?.toUtc() : null;
  }

  int get _liveOverrunMinutes {
    final serverValue = _possession['overrunMinutesLive'];
    if (serverValue is num && serverValue.toInt() > 0)
      return serverValue.toInt();
    final end = _plannedEnd;
    if (end == null || _status == WorkExecutionStatus.completed) return 0;
    final minutes = _now.difference(end).inMinutes;
    return minutes > 0 ? minutes : 0;
  }

  String get _windowLabel {
    final end = _plannedEnd;
    if (end == null) return 'Planned end not provided';
    final difference = end.difference(_now);
    final minutes = difference.inMinutes.abs();
    final hours = minutes ~/ 60;
    final remainder = minutes % 60;
    final duration = hours > 0 ? '${hours}h ${remainder}m' : '${remainder}m';
    return difference.isNegative ? 'Ended $duration ago' : 'Ends in $duration';
  }

  Future<void> _startWork() async {
    if (_allowedActions.contains('start-work')) {
      final possessionResult = await _runPossession('start-work');
      if (possessionResult == null) return;
    }
    await _saveWorkStatus(WorkExecutionStatus.started);
  }

  Future<Map<String, dynamic>?> _runPossession(String action) async {
    setState(() => _isLoading = true);
    try {
      final result = await widget.apiClient.postPossessionAction(
        possessionId: _possessionId,
        action: action,
      );
      if (!mounted) return result;
      setState(() {
        _isLoading = false;
        if (result['queued'] != true) _possession = result;
      });
      _showMessage(
        result['queued'] == true
            ? '${possessionActionLabel(action)} saved offline for replay.'
            : '${possessionActionLabel(action)} recorded.',
        result['queued'] == true
            ? RailOSTokens.status_caution_bg
            : RailOSTokens.status_ok_bg,
      );
      return result;
    } catch (error) {
      if (mounted) {
        setState(() => _isLoading = false);
        _showMessage(_recoveryMessage(error), RailOSTokens.status_critical_bg);
      }
      return null;
    }
  }

  Future<void> _saveWorkStatus(WorkExecutionStatus next) async {
    final taskStatus = _taskStatusFor(next);
    setState(() {
      _isLoading = true;
      _status = next;
    });
    try {
      final result = await widget.apiClient.updateWorkStatus(
        assignmentId: _taskId,
        executionStatus: next.name.toUpperCase(),
        taskStatus: taskStatus,
        possessionId: _possessionId,
      );
      if (!mounted) return;
      setState(() => _isLoading = false);
      _showMessage(
        result['queued'] == true
            ? 'Work update saved offline for replay.'
            : 'Work status updated.',
        result['queued'] == true
            ? RailOSTokens.status_caution_bg
            : RailOSTokens.status_ok_bg,
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      _showMessage(_recoveryMessage(error), RailOSTokens.status_critical_bg);
    }
  }

  String _taskStatusFor(WorkExecutionStatus status) {
    switch (status) {
      case WorkExecutionStatus.completed:
        return 'COMPLETED';
      case WorkExecutionStatus.cannotComplete:
        return 'DEFERRED';
      case WorkExecutionStatus.ready:
        return 'PENDING';
      case WorkExecutionStatus.started:
      case WorkExecutionStatus.inProgress:
      case WorkExecutionStatus.paused:
      case WorkExecutionStatus.delayed:
      case WorkExecutionStatus.completedPendingEvidence:
        return 'STARTED';
    }
  }

  void _showMessage(String message, Color background) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text(message), backgroundColor: background),
      );
  }

  String _recoveryMessage(Object error) {
    if (error is RailOSApiException) return error.message;
    return error.toString().replaceFirst('Exception: ', '');
  }

  RailOSStatus _statusTone() {
    switch (_status) {
      case WorkExecutionStatus.completed:
        return RailOSStatus.ok;
      case WorkExecutionStatus.cannotComplete:
        return RailOSStatus.critical;
      case WorkExecutionStatus.delayed:
      case WorkExecutionStatus.paused:
        return RailOSStatus.caution;
      case WorkExecutionStatus.ready:
        return RailOSStatus.info;
      default:
        return RailOSStatus.ok;
    }
  }

  Future<void> _openEvidence() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => TaskDetailScreen(
          task: widget.task,
          steps: _steps,
          apiClient: widget.apiClient,
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final overrunMinutes = _liveOverrunMinutes;
    final isOverrun = overrunMinutes > 0;
    final state = _possession['state']?.toString() ?? 'UNKNOWN';
    final stepsComplete =
        _steps.isNotEmpty &&
        _steps.every((step) => step.status == WorkExecutionStatus.completed);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Work · $_taskId',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontFamily: 'monospace'),
        ),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(RailOSTokens.spacingMd),
          children: [
            Text(
              'Work execution',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: RailOSTokens.spacingSm),
            Text(
              widget.task['title']?.toString() ?? 'Assigned possession work',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: RailOSTokens.spacingSm,
                    runSpacing: RailOSTokens.spacingSm,
                    children: [
                      RailOSStatusChip(
                        label: prettyRailName(_status.name),
                        status: _statusTone(),
                      ),
                      RailOSStatusChip(
                        label: prettyRailName(state),
                        status: possessionStatusFor(state),
                        compact: true,
                      ),
                    ],
                  ),
                  const SizedBox(height: RailOSTokens.spacingMd),
                  Text(
                    _windowLabel,
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(fontFamily: 'monospace'),
                  ),
                  const SizedBox(height: RailOSTokens.spacingXs),
                  buildRuleLabel(
                    context,
                    'SO-005 — tail overrun is measured against planned end',
                  ),
                ],
              ),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            if (isOverrun)
              Semantics(
                liveRegion: true,
                child: Container(
                  padding: const EdgeInsets.all(RailOSTokens.spacingMd),
                  decoration: BoxDecoration(
                    color: RailOSTokens.status_critical_bg,
                    borderRadius: BorderRadius.circular(
                      RailOSTokens.borderRadiusMd,
                    ),
                    border: Border.all(
                      color: RailOSTokens.status_critical_border,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: RailOSTokens.status_critical_fg,
                          ),
                          const SizedBox(width: RailOSTokens.spacingSm),
                          Expanded(
                            child: Text(
                              'CRITICAL: Work is ${overrunMinutes}m beyond the planned end.',
                              style: Theme.of(context).textTheme.titleMedium
                                  ?.copyWith(
                                    color: RailOSTokens.status_critical_text,
                                  ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: RailOSTokens.spacingSm),
                      Text(
                        'Stop and report the overrun so Control can protect the timetable.',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: RailOSTokens.status_critical_text,
                        ),
                      ),
                      if (_allowedActions.contains('declare-overrun')) ...[
                        const SizedBox(height: RailOSTokens.spacingSm),
                        RailOSPossessionActionButton(
                          action: 'declare-overrun',
                          onPressed: _isLoading
                              ? null
                              : () => _runPossession('declare-overrun'),
                          isLoading: _isLoading,
                        ),
                      ],
                    ],
                  ),
                ),
              )
            else
              RailOSPanel(
                child: Row(
                  children: [
                    const Icon(
                      Icons.timer_outlined,
                      color: RailOSTokens.status_caution_fg,
                    ),
                    const SizedBox(width: RailOSTokens.spacingSm),
                    Expanded(
                      child: Text(
                        'Clock is active. Keep the planned end visible while work is in progress.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: RailOSTokens.spacingMd),
            Text(
              'Ready → start → progress → outcome',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: RailOSTokens.spacingSm),
            if (_status == WorkExecutionStatus.ready)
              RailOSPossessionActionButton(
                action: 'start-work',
                onPressed: _isLoading ? null : _startWork,
                isLoading: _isLoading,
              )
            else ...[
              if (_status != WorkExecutionStatus.completed &&
                  _status != WorkExecutionStatus.cannotComplete) ...[
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isLoading
                            ? null
                            : () => _saveWorkStatus(
                                WorkExecutionStatus.inProgress,
                              ),
                        icon: const Icon(Icons.play_arrow_outlined),
                        label: const Text('In progress'),
                      ),
                    ),
                    const SizedBox(width: RailOSTokens.spacingSm),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isLoading
                            ? null
                            : () => _saveWorkStatus(WorkExecutionStatus.paused),
                        icon: const Icon(Icons.pause_outlined),
                        label: const Text('Pause'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: RailOSTokens.spacingSm),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isLoading
                            ? null
                            : () =>
                                  _saveWorkStatus(WorkExecutionStatus.delayed),
                        icon: const Icon(Icons.schedule_outlined),
                        label: const Text('Delay'),
                      ),
                    ),
                    const SizedBox(width: RailOSTokens.spacingSm),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isLoading
                            ? null
                            : () => _saveWorkStatus(
                                WorkExecutionStatus.cannotComplete,
                              ),
                        icon: const Icon(Icons.report_problem_outlined),
                        label: const Text('Cannot complete'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: RailOSTokens.spacingSm),
                RailOSPossessionActionButton(
                  action: 'completed',
                  onPressed: _isLoading
                      ? null
                      : () => _saveWorkStatus(WorkExecutionStatus.completed),
                  isLoading: _isLoading,
                ),
              ] else
                RailOSStatusChip(
                  label: _status == WorkExecutionStatus.completed
                      ? 'Work marked complete'
                      : 'Cannot complete — control notified',
                  status: _statusTone(),
                ),
            ],
            const SizedBox(height: RailOSTokens.spacingMd),
            SizedBox(
              width: double.infinity,
              height: RailOSTokens.minTouchTargetDp,
              child: OutlinedButton.icon(
                onPressed: _openEvidence,
                icon: const Icon(Icons.camera_alt_outlined),
                label: Text(
                  stepsComplete
                      ? 'Review verified evidence'
                      : 'Open evidence steps',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
