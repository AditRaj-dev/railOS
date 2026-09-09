import 'package:flutter/material.dart';

import '../models/evidence_models.dart';
import '../screens/dashboard_screen.dart';
import '../services/api_client.dart';
import '../theme/railos_tokens.dart';
import 'emergency_action.dart';

/// Top-level shell for RailOS Field Operations providing a 4-tab bottom navigation bar:
/// 1. Tasks (Assigned tasks and macro step workflows)
/// 2. Possessions (Day-of possession windows and live authority records)
/// 3. Activity (Offline evidence sync queue and event timeline)
/// 4. More (System info, statutory rulebook references, logout)
///
/// Emergency hazard report is permanently accessible in the AppBar across all tabs.
class FieldShell extends StatefulWidget {
  final RailOSApiClient apiClient;
  final VoidCallback onLogout;

  const FieldShell({
    super.key,
    required this.apiClient,
    required this.onLogout,
  });

  @override
  State<FieldShell> createState() => _FieldShellState();
}

class _FieldShellState extends State<FieldShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: [
          DashboardScreen(
            apiClient: widget.apiClient,
            onLogout: widget.onLogout,
          ),
          _PossessionsTab(apiClient: widget.apiClient),
          _ActivityTab(apiClient: widget.apiClient),
          _MoreTab(
            apiClient: widget.apiClient,
            onLogout: widget.onLogout,
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) => setState(() => _currentIndex = index),
        backgroundColor: RailOSTokens.bg_surface,
        indicatorColor: RailOSTokens.accent.withValues(alpha: 0.15),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.assignment_outlined),
            selectedIcon: Icon(Icons.assignment, color: RailOSTokens.accent),
            label: 'Tasks',
          ),
          NavigationDestination(
            icon: Icon(Icons.shield_outlined),
            selectedIcon: Icon(Icons.shield, color: RailOSTokens.accent),
            label: 'Possessions',
          ),
          NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history, color: RailOSTokens.accent),
            label: 'Activity',
          ),
          NavigationDestination(
            icon: Icon(Icons.more_horiz_outlined),
            selectedIcon: Icon(Icons.more_horiz, color: RailOSTokens.accent),
            label: 'More',
          ),
        ],
      ),
    );
  }
}

class _PossessionsTab extends StatefulWidget {
  final RailOSApiClient apiClient;

  const _PossessionsTab({required this.apiClient});

  @override
  State<_PossessionsTab> createState() => _PossessionsTabState();
}

class _PossessionsTabState extends State<_PossessionsTab> {
  List<Map<String, dynamic>> _possessions = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final items = await widget.apiClient.fetchMyPossessions();
      if (mounted) setState(() => _possessions = items);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Live Possessions'),
        actions: [
          EmergencyAppBarAction(apiClient: widget.apiClient),
          const SizedBox(width: 8),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _fetch,
        child: _isLoading
            ? const Center(
                child: SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(color: RailOSTokens.accent, strokeWidth: 2),
                ),
              )
            : _error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.cloud_off_outlined, size: 40, color: RailOSTokens.text_muted),
                          const SizedBox(height: 8),
                          Text(_error!, style: const TextStyle(color: RailOSTokens.text_muted), textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: _fetch,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                : _possessions.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.shield_outlined, size: 44, color: RailOSTokens.text_muted),
                            const SizedBox(height: 8),
                            const Text(
                              'No open possessions for your section',
                              style: TextStyle(color: RailOSTokens.text_muted),
                            ),
                            const SizedBox(height: 12),
                            OutlinedButton.icon(
                              onPressed: _fetch,
                              icon: const Icon(Icons.refresh),
                              label: const Text('Refresh'),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(RailOSTokens.spacingMd),
                        itemCount: _possessions.length,
                        itemBuilder: (context, index) {
                          final p = _possessions[index];
                          final id = p['possessionId']?.toString() ?? 'POS-00';
                          final state = p['state']?.toString() ?? 'SANCTIONED';
                          final section = p['sectionId']?.toString() ?? '';
                          final track = p['track']?.toString() ?? '';
                          return Card(
                            margin: const EdgeInsets.only(bottom: RailOSTokens.spacingSm),
                            color: RailOSTokens.bg_panel,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                              side: const BorderSide(color: RailOSTokens.border_default),
                            ),
                            child: ListTile(
                              title: Text(
                                '$id · $section $track',
                                style: const TextStyle(
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.bold,
                                  color: RailOSTokens.text_primary,
                                ),
                              ),
                              subtitle: Text(
                                'State: $state',
                                style: const TextStyle(color: RailOSTokens.text_secondary, fontSize: 12),
                              ),
                              trailing: const Icon(Icons.chevron_right, color: RailOSTokens.text_muted),
                              onTap: () {
                                Navigator.pushNamed(context, '/possession', arguments: p);
                              },
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}

class _ActivityTab extends StatelessWidget {
  final RailOSApiClient apiClient;

  const _ActivityTab({required this.apiClient});

  @override
  Widget build(BuildContext context) {
    final queue = apiClient.queue;
    final pending = queue.pendingQueue;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Activity & Sync Queue'),
        actions: [
          EmergencyAppBarAction(apiClient: apiClient),
          const SizedBox(width: 8),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(RailOSTokens.spacingMd),
        children: [
          Card(
            color: RailOSTokens.bg_panel,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
              side: const BorderSide(color: RailOSTokens.border_default),
            ),
            child: Padding(
              padding: const EdgeInsets.all(RailOSTokens.spacingMd),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.sync, size: 20, color: RailOSTokens.accent),
                      const SizedBox(width: 8),
                      Text(
                        'Offline Queue (${pending.length} items)',
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: RailOSTokens.text_primary,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    pending.isEmpty
                        ? 'All captured proofs and actions are synchronized with RailOS server.'
                        : '${pending.length} evidence items held locally pending upload connectivity.',
                    style: const TextStyle(color: RailOSTokens.text_secondary, fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: RailOSTokens.spacingMd),
          if (pending.isNotEmpty) ...[
            const Text(
              'Queued Evidence Records',
              style: TextStyle(
                fontSize: 13,
                fontFamily: 'monospace',
                fontWeight: FontWeight.bold,
                color: RailOSTokens.text_secondary,
              ),
            ),
            const SizedBox(height: RailOSTokens.spacingSm),
            ...pending.map((e) => Card(
                  margin: const EdgeInsets.only(bottom: RailOSTokens.spacingSm),
                  color: RailOSTokens.bg_surface,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                    side: const BorderSide(color: RailOSTokens.border_subtle),
                  ),
                  child: ListTile(
                    leading: Icon(
                      e.kind == EvidenceKind.photo ? Icons.photo_camera : Icons.videocam,
                      color: RailOSTokens.accent,
                    ),
                    title: Text(
                      '${e.stepId} // Task ${e.taskId}',
                      style: const TextStyle(fontFamily: 'monospace', fontSize: 12, fontWeight: FontWeight.bold, color: RailOSTokens.text_primary),
                    ),
                    subtitle: Text(
                      'ID: ${e.evidenceId} · ${e.status.name}',
                      style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: RailOSTokens.text_muted),
                    ),
                  ),
                )),
          ],
        ],
      ),
    );
  }
}

class _MoreTab extends StatelessWidget {
  final RailOSApiClient apiClient;
  final VoidCallback onLogout;

  const _MoreTab({
    required this.apiClient,
    required this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    final session = apiClient.queue.currentSession;
    return Scaffold(
      appBar: AppBar(
        title: const Text('More Operations'),
        actions: [
          EmergencyAppBarAction(apiClient: apiClient),
          const SizedBox(width: 8),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(RailOSTokens.spacingMd),
        children: [
          Card(
            color: RailOSTokens.bg_panel,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
              side: const BorderSide(color: RailOSTokens.border_default),
            ),
            child: Padding(
              padding: const EdgeInsets.all(RailOSTokens.spacingMd),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    session?.name ?? 'Field Operator',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: RailOSTokens.text_primary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'EMP: ${session?.employeeId ?? '—'} · Role: ${session?.normalizedRole ?? 'FIELD_SUPERVISOR'}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontFamily: 'monospace',
                      color: RailOSTokens.text_secondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: RailOSTokens.spacingMd),
          ListTile(
            leading: const Icon(Icons.warning_amber_rounded, color: RailOSTokens.status_critical_fg),
            title: const Text('Report Emergency Hazard', style: TextStyle(color: RailOSTokens.text_primary, fontWeight: FontWeight.w600)),
            subtitle: const Text('Immediate safety-critical fracture, OHE drop, or obstacle', style: TextStyle(fontSize: 12, color: RailOSTokens.text_secondary)),
            trailing: const Icon(Icons.chevron_right, color: RailOSTokens.text_muted),
            onTap: () {
              Navigator.pushNamed(context, '/emergency');
            },
          ),
          const Divider(color: RailOSTokens.border_subtle),
          ListTile(
            leading: const Icon(Icons.menu_book_outlined, color: RailOSTokens.accent),
            title: const Text('Statutory Rules & Manuals', style: TextStyle(color: RailOSTokens.text_primary, fontWeight: FontWeight.w600)),
            subtitle: const Text('IRPWM 806 detonator rules, ACTM 20.5 PTW protocol, G&SR 15.08', style: TextStyle(fontSize: 12, color: RailOSTokens.text_secondary)),
          ),
          const Divider(color: RailOSTokens.border_subtle),
          ListTile(
            leading: const Icon(Icons.logout, color: RailOSTokens.status_caution_fg),
            title: const Text('Sign Out', style: TextStyle(color: RailOSTokens.status_caution_fg, fontWeight: FontWeight.w600)),
            subtitle: const Text('Clears cached active session entitlement', style: TextStyle(fontSize: 12, color: RailOSTokens.text_secondary)),
            onTap: onLogout,
          ),
        ],
      ),
    );
  }
}
