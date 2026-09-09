import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../shell/emergency_action.dart';
import '../theme/railos_tokens.dart';
import '../theme/railos_widgets.dart';
import 'possession_ui.dart';

class IsolationScreen extends StatefulWidget {
  final Map<String, dynamic> possession;
  final RailOSApiClient apiClient;

  const IsolationScreen({
    super.key,
    required this.possession,
    required this.apiClient,
  });

  @override
  State<IsolationScreen> createState() => _IsolationScreenState();
}

class _IsolationScreenState extends State<IsolationScreen> {
  late Map<String, dynamic> _possession;
  final _t351Controller = TextEditingController();
  final _isolatorController = TextEditingController(text: 'ISO-01');
  final _detonatorController = TextEditingController(text: '3');
  final _noteController = TextEditingController();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _possession = Map<String, dynamic>.from(widget.possession);
    final t351 = _map('formT351');
    _t351Controller.text = t351['formNumber']?.toString() ?? '';
    final permit = _map('permitToWork');
    _isolatorController.text = permit['isolatorNumber']?.toString() ?? 'ISO-01';
  }

  @override
  void dispose() {
    _t351Controller.dispose();
    _isolatorController.dispose();
    _detonatorController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  String _role() =>
      widget.apiClient.queue.currentSession?.normalizedRole ??
      'FIELD_SUPERVISOR';

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

  String _id() => _possession['possessionId']?.toString() ?? '';

  Future<void> _run(
    String action, {
    String? formReference,
    Map<String, dynamic>? details,
    int? detonatorCount,
  }) async {
    setState(() => _isLoading = true);
    try {
      final result = await widget.apiClient.postPossessionAction(
        possessionId: _id(),
        action: action,
        formReference: formReference,
        details: details,
        detonatorCount: detonatorCount,
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
                ? '${possessionActionLabel(action)} saved offline. It will replay when connected.'
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

  Widget _artifact({
    required String title,
    required String formNumber,
    required String status,
    required String rule,
    required IconData icon,
    required Widget child,
  }) {
    return RailOSPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: RailOSTokens.accent),
              const SizedBox(width: RailOSTokens.spacingSm),
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              RailOSStatusChip(
                label: prettyRailName(status),
                status:
                    status.toUpperCase() == 'ISSUED' ||
                        status.toUpperCase() == 'ENDORSED'
                    ? RailOSStatus.ok
                    : RailOSStatus.info,
                compact: true,
              ),
            ],
          ),
          const SizedBox(height: RailOSTokens.spacingSm),
          Text(
            'Form: $formNumber',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(fontFamily: 'monospace'),
          ),
          const SizedBox(height: RailOSTokens.spacingXs),
          buildRuleLabel(context, rule),
          const SizedBox(height: RailOSTokens.spacingMd),
          child,
        ],
      ),
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

  Widget _t351Card() {
    final t351 = _map('formT351');
    final status = t351['status']?.toString() ?? 'NOT_ISSUED';
    return _artifact(
      title: 'T/351 disconnection authority',
      formNumber: t351['formNumber']?.toString() ?? 'Pending issue',
      status: status,
      rule: 'HC-005',
      icon: Icons.description_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextFormField(
            controller: _t351Controller,
            decoration: const InputDecoration(
              labelText: 'T/351 form reference',
              helperText: 'Station Master records the issued form number.',
            ),
          ),
          _action(
            'issue-t351',
            onPressed: () => _run(
              'issue-t351',
              formReference: _t351Controller.text.trim().isEmpty
                  ? null
                  : _t351Controller.text.trim(),
            ),
          ),
          _action('endorse-t351', onPressed: () => _run('endorse-t351')),
        ],
      ),
    );
  }

  Widget _ptwCard() {
    final permit = _map('permitToWork');
    final status = permit['status']?.toString() ?? 'NOT_ISSUED';
    final isolators = permit['isolators'] is List
        ? (permit['isolators'] as List)
              .map((value) => value.toString())
              .join(', ')
        : permit['isolatorNumber']?.toString() ?? 'No isolator recorded';
    return _artifact(
      title: 'ETR-3 permit to work',
      formNumber: permit['ptwNumber']?.toString() ?? 'Pending issue',
      status: status,
      rule: 'HC-003 / HC-004',
      icon: Icons.power_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Isolator list: $isolators',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: RailOSTokens.spacingSm),
          TextFormField(
            controller: _isolatorController,
            decoration: const InputDecoration(
              labelText: 'Isolator confirmed',
              helperText: 'Record the isolator before earthing and PTW issue.',
            ),
          ),
          _action(
            'confirm-earthing',
            onPressed: () => _run(
              'confirm-earthing',
              details: {'isolatorNumber': _isolatorController.text.trim()},
            ),
          ),
          _action(
            'issue-ptw',
            onPressed: () => _run(
              'issue-ptw',
              details: {'isolatorNumber': _isolatorController.text.trim()},
            ),
          ),
        ],
      ),
    );
  }

  Widget _protectionCard() {
    final protection = _map('protectionRecord');
    final count = protection['detonatorCount']?.toString() ?? 'Not recorded';
    return _artifact(
      title: 'Protection and detonators',
      formNumber: protection.isEmpty ? 'Pending plant' : 'PROT-${_id()}',
      status: protection.isEmpty ? 'PENDING' : 'PLACED',
      rule: 'IRPWM 806 / HC-005',
      icon: Icons.shield_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Recorded detonator count: $count',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: RailOSTokens.spacingSm),
          TextFormField(
            controller: _detonatorController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Detonator count',
              helperText:
                  'Enter the physical count before planting protection.',
            ),
          ),
          _action(
            'plant-protection',
            onPressed: () {
              final count = int.tryParse(_detonatorController.text.trim());
              if (count == null || count < 1) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Enter a detonator count of at least 1.'),
                    backgroundColor: RailOSTokens.status_critical_bg,
                  ),
                );
                return;
              }
              _run('plant-protection', detonatorCount: count);
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final role = _role();
    final state = _possession['state']?.toString() ?? 'UNKNOWN';
    final t351Required =
        _possession['requiresT351'] == true || role == 'STATION_MASTER';
    final ptwRequired = _possession['requiresPTW'] == true || role == 'TPC';
    final protectionVisible =
        role == 'ENGINEERING' || role == 'FIELD_SUPERVISOR' || role == 'ADMIN';

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Isolation · ${_id()}',
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
              'Isolation and disconnection',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: RailOSTokens.spacingSm),
            Text(
              'Your role: ${prettyRailName(role)}. Each artefact stays tied to a form number and its governing rule.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            RailOSStatusChip(
              label: prettyRailName(state),
              status: possessionStatusFor(state),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            if (t351Required) ...[
              _t351Card(),
              const SizedBox(height: RailOSTokens.spacingMd),
            ],
            if (ptwRequired) ...[
              _ptwCard(),
              const SizedBox(height: RailOSTokens.spacingMd),
            ],
            if (protectionVisible) ...[
              _protectionCard(),
              const SizedBox(height: RailOSTokens.spacingMd),
            ],
            RailOSPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Authority note (optional)',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: RailOSTokens.spacingSm),
                  TextFormField(
                    controller: _noteController,
                    maxLines: 2,
                    decoration: const InputDecoration(
                      labelText: 'Reason or site observation',
                      helperText:
                          'This note is added to the transition audit record.',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: RailOSTokens.spacingMd),
            if (_allowedActions.contains('start-isolation'))
              RailOSPossessionActionButton(
                action: 'start-isolation',
                onPressed: _isLoading ? null : () => _run('start-isolation'),
                isLoading: _isLoading,
              ),
            if (_allowedActions.isEmpty)
              RailOSPanel(
                child: Text(
                  'No isolation action is enabled for your role in this possession state. Ask the next authority to act online.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
