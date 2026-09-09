import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../shell/emergency_action.dart';
import '../theme/railos_tokens.dart';
import '../theme/railos_widgets.dart';
import 'possession_ui.dart';

class HandbackScreen extends StatefulWidget {
  final Map<String, dynamic> possession;
  final RailOSApiClient apiClient;

  const HandbackScreen({
    super.key,
    required this.possession,
    required this.apiClient,
  });

  @override
  State<HandbackScreen> createState() => _HandbackScreenState();
}

class _HandbackScreenState extends State<HandbackScreen> {
  late Map<String, dynamic> _possession;
  final _durationController = TextEditingController(text: '30');
  final _noteController = TextEditingController();
  int _tsrSpeed = 20;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _possession = Map<String, dynamic>.from(widget.possession);
    final test = _map('correspondenceTest');
    if (test['durationMinutes'] is num) {
      _durationController.text = test['durationMinutes'].toString();
    }
    final certificate = _map('fitnessCertificate');
    if (certificate['tsrSpeedKmph'] is num &&
        [20, 45, 75].contains((certificate['tsrSpeedKmph'] as num).toInt())) {
      _tsrSpeed = (certificate['tsrSpeedKmph'] as num).toInt();
    }
  }

  @override
  void dispose() {
    _durationController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  Map<String, dynamic> _map(String key) {
    final value = _possession[key];
    return value is Map
        ? Map<String, dynamic>.from(value)
        : <String, dynamic>{};
  }

  List<String> get _allowedActions =>
      (_possession['allowedActions'] as List? ?? const [])
          .map((value) => value.toString())
          .toList();

  String get _id => _possession['possessionId']?.toString() ?? '';
  String get _role =>
      widget.apiClient.queue.currentSession?.normalizedRole ??
      'FIELD_SUPERVISOR';

  Future<void> _run(
    String action, {
    int? durationMinutes,
    int? tsrSpeedKmph,
  }) async {
    setState(() => _isLoading = true);
    try {
      final result = await widget.apiClient.postPossessionAction(
        possessionId: _id,
        action: action,
        durationMinutes: durationMinutes,
        tsrSpeedKmph: tsrSpeedKmph,
        note: _noteController.text.trim().isEmpty
            ? null
            : _noteController.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        if (result['queued'] != true) _possession = result;
      });
      final queued = result['queued'] == true;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            queued
                ? '${possessionActionLabel(action)} saved offline for replay.'
                : '${possessionActionLabel(action)} recorded.',
          ),
          backgroundColor: queued
              ? RailOSTokens.status_caution_bg
              : RailOSTokens.status_ok_bg,
        ),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_recoveryMessage(error)),
          backgroundColor: RailOSTokens.status_critical_bg,
        ),
      );
    }
  }

  String _recoveryMessage(Object error) {
    if (error is RailOSApiException) return error.message;
    return error.toString().replaceFirst('Exception: ', '');
  }

  Future<void> _recordTest() async {
    final duration = int.tryParse(_durationController.text.trim());
    if (duration == null || duration < 30) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Correspondence testing must run for at least 30 minutes.',
          ),
          backgroundColor: RailOSTokens.status_critical_bg,
        ),
      );
      return;
    }
    await _run('record-correspondence-test', durationMinutes: duration);
  }

  Widget _checklist() {
    final entries = (_possession['handbackChecklist'] as List? ?? const [])
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
    if (entries.isEmpty) {
      return Text(
        'The server has not returned a handback checklist yet. Refresh after the possession enters testing.',
        style: Theme.of(context).textTheme.bodyMedium,
      );
    }
    return Column(
      children: entries.map((entry) {
        final satisfied = entry['satisfied'] == true;
        return Semantics(
          container: true,
          label:
              '${entry['item'] ?? 'Checklist item'}: ${satisfied ? 'complete' : 'pending'}',
          child: Padding(
            padding: const EdgeInsets.only(bottom: RailOSTokens.spacingSm),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  satisfied
                      ? Icons.check_circle_outline
                      : Icons.radio_button_unchecked,
                  color: satisfied
                      ? RailOSTokens.status_ok_fg
                      : RailOSTokens.text_muted,
                ),
                const SizedBox(width: RailOSTokens.spacingSm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry['item']?.toString() ?? 'Checklist item',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: RailOSTokens.spacingXs),
                      Text(
                        '${satisfied ? 'Complete' : 'Pending'} · ${entry['rule'] ?? 'Rule not provided'}',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _action(String action, {VoidCallback? onPressed}) {
    if (!_allowedActions.contains(action)) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: RailOSTokens.spacingSm),
      child: RailOSPossessionActionButton(
        action: action,
        onPressed: _isLoading ? null : onPressed,
        isLoading: _isLoading,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = _possession['state']?.toString() ?? 'UNKNOWN';
    final test = _map('correspondenceTest');
    final permit = _map('permitToWork');
    final certificate = _map('fitnessCertificate');
    final hasPendingActions = _allowedActions.isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Handback · $_id',
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
        child: ListView(
          padding: const EdgeInsets.all(RailOSTokens.spacingMd),
          children: [
            Text(
              'Testing and handback',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: RailOSTokens.spacingSm),
            Text(
              'Role: ${prettyRailName(_role)}. Complete each item before the server accepts the final close.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSStatusChip(
              label: prettyRailName(state),
              status: possessionStatusFor(state),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Handback checklist',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: RailOSTokens.spacingMd),
                  _checklist(),
                ],
              ),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Correspondence test',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: RailOSTokens.spacingXs),
                  buildRuleLabel(context, 'HC-006 — minimum 30 minutes'),
                  const SizedBox(height: RailOSTokens.spacingSm),
                  if (test.isNotEmpty)
                    Text(
                      'Recorded ${test['durationMinutes'] ?? '—'} minutes • ${test['passed'] == true ? 'Passed' : 'Review required'}',
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(fontFamily: 'monospace'),
                    ),
                  TextFormField(
                    controller: _durationController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Test duration (minutes)',
                      helperText:
                          'The server also enforces the 30-minute floor.',
                    ),
                  ),
                  _action('start-testing'),
                  _action('record-correspondence-test', onPressed: _recordTest),
                ],
              ),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Power and permit close',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: RailOSTokens.spacingSm),
                  Text(
                    permit.isEmpty
                        ? 'No PTW artefact is attached to this possession.'
                        : 'Permit ${permit['ptwNumber'] ?? 'not numbered'} • ${permit['status'] ?? 'status not provided'}',
                    style: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.copyWith(fontFamily: 'monospace'),
                  ),
                  _action('remove-discharge-rods'),
                  _action('cancel-ptw'),
                  _action('re-energise'),
                ],
              ),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Fitness certificate',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: RailOSTokens.spacingXs),
                  buildRuleLabel(
                    context,
                    'HC-018 — SSE P-Way certification with TSR ladder',
                  ),
                  const SizedBox(height: RailOSTokens.spacingSm),
                  if (certificate.isNotEmpty)
                    Text(
                      'Certificate ${certificate['certificateNumber'] ?? 'not numbered'} • TSR ${certificate['tsrSpeedKmph'] ?? '—'} km/h',
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(fontFamily: 'monospace'),
                    ),
                  DropdownButtonFormField<int>(
                    initialValue: _tsrSpeed,
                    decoration: const InputDecoration(
                      labelText: 'Temporary speed restriction',
                      helperText: 'Choose the safe 20 / 45 / 75 km/h ladder.',
                    ),
                    items: const [20, 45, 75]
                        .map(
                          (speed) => DropdownMenuItem<int>(
                            value: speed,
                            child: Text('$speed km/h'),
                          ),
                        )
                        .toList(),
                    onChanged: (speed) {
                      if (speed != null) setState(() => _tsrSpeed = speed);
                    },
                  ),
                  _action(
                    'certify-fitness',
                    onPressed: () =>
                        _run('certify-fitness', tsrSpeedKmph: _tsrSpeed),
                  ),
                ],
              ),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Handback note (optional)',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: RailOSTokens.spacingSm),
                  TextFormField(
                    controller: _noteController,
                    maxLines: 2,
                    decoration: const InputDecoration(
                      labelText: 'Record a handback observation',
                      helperText:
                          'The note travels with the transition audit record.',
                    ),
                  ),
                  _action('request-handback'),
                ],
              ),
            ),
            if (!hasPendingActions) ...[
              const SizedBox(height: RailOSTokens.spacingMd),
              RailOSPanel(
                child: Text(
                  'No handback action is enabled for your role in this state. Refresh after the previous authority records its step.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
