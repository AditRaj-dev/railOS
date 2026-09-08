import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/evidence_models.dart';
import '../services/api_client.dart';
import '../storage/offline_evidence_queue.dart';
import '../theme/railos_tokens.dart';
import 'emergency_screen.dart';
import 'task_detail_screen.dart';

class DashboardScreen extends StatefulWidget {
  final RailOSApiClient apiClient;
  final VoidCallback onLogout;

  const DashboardScreen({
    super.key,
    required this.apiClient,
    required this.onLogout,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<Map<String, dynamic>> _tasks = [];
  bool _isLoading = true;
  final OfflineEvidenceQueue _queue = OfflineEvidenceQueue();

  @override
  void initState() {
    super.initState();
    _loadTasks();
    _queue.addListener(_onQueueChanged);
  }

  @override
  void dispose() {
    _queue.removeListener(_onQueueChanged);
    super.dispose();
  }

  void _onQueueChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _loadTasks() async {
    setState(() => _isLoading = true);
    final tasks = await widget.apiClient.fetchMyAssignments();
    if (mounted) {
      setState(() {
        _tasks = tasks;
        _isLoading = false;
      });
    }
  }

  Future<void> _syncPending() async {
    for (final evidence in List<CapturedEvidence>.from(_queue.pendingQueue)) {
      if (evidence.status == EvidenceStatus.uploadPending) {
        try {
          await widget.apiClient.syncEvidence(evidence);
        } catch (_) {}
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.apiClient.queue.currentSession;
    final pendingCount = _queue.pendingQueue
        .where((e) => e.status == EvidenceStatus.uploadPending)
        .length;

    return Scaffold(
      backgroundColor: RailOSTokens.bg_darkRoot,
      appBar: AppBar(
        backgroundColor: RailOSTokens.bg_darkSurface,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              AppStrings.get('app_title'),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            Text(
              session != null ? '${session.name} (${session.employeeId})' : 'Field Supervisor',
              style: const TextStyle(fontSize: 11, color: Colors.white70),
            ),
          ],
        ),
        actions: [
          // Language toggle
          IconButton(
            icon: const Icon(Icons.language, color: Colors.cyan),
            tooltip: AppStrings.get('settings_lang'),
            onPressed: () {
              setState(() {
                AppStrings.currentLanguage =
                    AppStrings.currentLanguage == 'en' ? 'hi' : 'en';
              });
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.white70),
            onPressed: widget.onLogout,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Banner: Emergency Report + Offline Queue Sync
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: RailOSTokens.spacingMd,
                vertical: RailOSTokens.spacingSm,
              ),
              color: RailOSTokens.bg_darkElevated,
              child: Row(
                children: [
                  // Emergency hazard report button
                  Expanded(
                    child: SizedBox(
                      height: RailOSTokens.minTouchTargetDp,
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.warning_amber_rounded, color: Colors.white),
                        label: Text(
                          AppStrings.get('emergency_btn'),
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: RailOSTokens.primary_safetyRed,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                          ),
                        ),
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => EmergencyScreen(apiClient: widget.apiClient),
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  const SizedBox(width: RailOSTokens.spacingSm),

                  // Offline queue indicator
                  if (pendingCount > 0)
                    InkWell(
                      onTap: _syncPending,
                      borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                      child: Container(
                        height: RailOSTokens.minTouchTargetDp,
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          color: RailOSTokens.status_caution_bg,
                          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                          border: Border.all(color: RailOSTokens.status_caution_border),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.sync, color: Colors.amberAccent, size: 18),
                            const SizedBox(width: 6),
                            Text(
                              '$pendingCount Sync',
                              style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),

            // Section Header
            Padding(
              padding: const EdgeInsets.all(RailOSTokens.spacingMd),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    AppStrings.get('assigned_tasks'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.refresh, color: Colors.cyan),
                    onPressed: _loadTasks,
                  ),
                ],
              ),
            ),

            // Tasks List
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: Colors.cyan))
                  : _tasks.isEmpty
                      ? const Center(
                          child: Text(
                            'No assigned tasks for this shift.',
                            style: TextStyle(color: Colors.white54),
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.symmetric(horizontal: RailOSTokens.spacingMd),
                          itemCount: _tasks.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: RailOSTokens.spacingSm),
                          itemBuilder: (ctx, i) {
                            final task = _tasks[i];
                            final steps = (task['steps'] as List? ?? [])
                                .map((s) => WorkStep.fromJson(s as Map<String, dynamic>))
                                .toList();

                            return Card(
                              color: RailOSTokens.bg_darkSurface,
                              shape: RoundedRectangleBorder(
                                side: const BorderSide(color: RailOSTokens.bg_darkBorder),
                                borderRadius:
                                    BorderRadius.circular(RailOSTokens.borderRadiusMd),
                              ),
                              child: InkWell(
                                borderRadius:
                                    BorderRadius.circular(RailOSTokens.borderRadiusMd),
                                onTap: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => TaskDetailScreen(
                                        task: task,
                                        steps: steps,
                                        apiClient: widget.apiClient,
                                      ),
                                    ),
                                  );
                                },
                                child: Padding(
                                  padding: const EdgeInsets.all(RailOSTokens.spacingMd),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                        children: [
                                          Text(
                                            task['taskId'] as String? ?? '',
                                            style: const TextStyle(
                                              color: Colors.cyanAccent,
                                              fontFamily: 'monospace',
                                              fontWeight: FontWeight.bold,
                                              fontSize: 13,
                                            ),
                                          ),
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 8,
                                              vertical: 2,
                                            ),
                                            decoration: BoxDecoration(
                                              color: Colors.blueGrey.shade900,
                                              borderRadius: BorderRadius.circular(4),
                                              border: Border.all(color: Colors.blueGrey),
                                            ),
                                            child: Text(
                                              task['department'] as String? ?? 'ENGG',
                                              style: const TextStyle(
                                                color: Colors.white,
                                                fontSize: 10,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        task['title'] as String? ?? 'Maintenance Task',
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 15,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 10),
                                      Row(
                                        children: [
                                          const Icon(Icons.checklist, size: 16, color: Colors.white54),
                                          const SizedBox(width: 4),
                                          Text(
                                            '${steps.length} Macro Steps (${steps.where((s) => s.status == WorkExecutionStatus.completed).length} Verified)',
                                            style: const TextStyle(
                                              color: Colors.white70,
                                              fontSize: 12,
                                            ),
                                          ),
                                          const Spacer(),
                                          const Icon(Icons.arrow_forward_ios,
                                              size: 14, color: Colors.white54),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
