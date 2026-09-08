import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/evidence_models.dart';
import '../services/api_client.dart';
import '../storage/offline_evidence_queue.dart';
import '../theme/railos_tokens.dart';
import '../theme/railos_widgets.dart';
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
      backgroundColor: RailOSTokens.bg_canvas,
      appBar: AppBar(
        backgroundColor: RailOSTokens.bg_surface,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              AppStrings.get('app_title'),
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
                color: RailOSTokens.text_primary,
                letterSpacing: 0.3,
              ),
            ),
            const SizedBox(height: 1),
            Text(
              session != null ? '${session.name} • ${session.employeeId}' : 'Field Supervisor',
              style: const TextStyle(
                fontSize: 11,
                fontFamily: 'monospace',
                color: RailOSTokens.text_muted,
              ),
            ),
          ],
        ),
        actions: [
          // Language toggle
          IconButton(
            icon: const Icon(Icons.language, color: RailOSTokens.text_secondary, size: 20),
            tooltip: AppStrings.get('settings_lang'),
            onPressed: () {
              setState(() {
                AppStrings.currentLanguage =
                    AppStrings.currentLanguage == 'en' ? 'hi' : 'en';
              });
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: RailOSTokens.text_secondary, size: 20),
            tooltip: 'Logout',
            onPressed: widget.onLogout,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Top Operational Banner: Emergency Dispatch + Offline Queue Sync
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: RailOSTokens.spacingMd,
                vertical: RailOSTokens.spacingSm,
              ),
              decoration: const BoxDecoration(
                color: RailOSTokens.bg_surface,
                border: Border(
                  bottom: BorderSide(color: RailOSTokens.border_default, width: 1),
                ),
              ),
              child: Row(
                children: [
                  // Emergency hazard report button with disciplined critical status styling
                  Expanded(
                    child: SizedBox(
                      height: RailOSTokens.minTouchTargetDp,
                      child: ElevatedButton.icon(
                        icon: const Icon(
                          Icons.warning_amber_rounded,
                          color: RailOSTokens.status_critical_fg,
                          size: 18,
                        ),
                        label: Text(
                          AppStrings.get('emergency_btn'),
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                            letterSpacing: 0.3,
                            color: RailOSTokens.status_critical_text,
                          ),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: RailOSTokens.status_critical_bg,
                          foregroundColor: RailOSTokens.status_critical_text,
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
                              builder: (_) => EmergencyScreen(apiClient: widget.apiClient),
                            ),
                          );
                        },
                      ),
                    ),
                  ),

                  // Offline queue sync indicator
                  if (pendingCount > 0) ...[
                    const SizedBox(width: RailOSTokens.spacingSm),
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
                            const Icon(
                              Icons.sync,
                              color: RailOSTokens.status_caution_fg,
                              size: 16,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              '$pendingCount Sync',
                              style: const TextStyle(
                                color: RailOSTokens.status_caution_text,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Section Header
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: RailOSTokens.spacingMd,
                vertical: RailOSTokens.spacingSm,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Text(
                        AppStrings.get('assigned_tasks'),
                        style: const TextStyle(
                          color: RailOSTokens.text_primary,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.3,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: RailOSTokens.bg_elevated,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: RailOSTokens.border_subtle),
                        ),
                        child: Text(
                          '${_tasks.length}',
                          style: const TextStyle(
                            color: RailOSTokens.text_secondary,
                            fontSize: 10,
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.refresh,
                      color: RailOSTokens.text_secondary,
                      size: 18,
                    ),
                    tooltip: 'Refresh Assignments',
                    onPressed: _loadTasks,
                  ),
                ],
              ),
            ),

            // Tasks List
            Expanded(
              child: _isLoading
                  ? const Center(
                      child: SizedBox(
                        width: 28,
                        height: 28,
                        child: CircularProgressIndicator(
                          color: RailOSTokens.accent,
                          strokeWidth: 2,
                        ),
                      ),
                    )
                  : _tasks.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(
                                Icons.inbox_outlined,
                                size: 40,
                                color: RailOSTokens.text_muted,
                              ),
                              const SizedBox(height: 8),
                              const Text(
                                'No assigned tasks for this shift.',
                                style: TextStyle(color: RailOSTokens.text_secondary, fontSize: 13),
                              ),
                            ],
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.symmetric(
                            horizontal: RailOSTokens.spacingMd,
                            vertical: RailOSTokens.spacingXs,
                          ),
                          itemCount: _tasks.length,
                          separatorBuilder: (_, _) =>
                              const SizedBox(height: RailOSTokens.spacingSm),
                          itemBuilder: (ctx, i) {
                            final task = _tasks[i];
                            final steps = (task['steps'] as List? ?? [])
                                .map((s) => WorkStep.fromJson(s as Map<String, dynamic>))
                                .toList();
                            final completedSteps = steps
                                .where((s) => s.status == WorkExecutionStatus.completed)
                                .length;
                            final isFullyVerified = steps.isNotEmpty && completedSteps == steps.length;

                            return Container(
                              decoration: BoxDecoration(
                                color: RailOSTokens.bg_panel,
                                borderRadius:
                                    BorderRadius.circular(RailOSTokens.borderRadiusMd),
                                border: Border.all(
                                  color: isFullyVerified
                                      ? RailOSTokens.status_ok_border
                                      : RailOSTokens.border_default,
                                  width: 1,
                                ),
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
                                              color: RailOSTokens.status_info_fg,
                                              fontFamily: 'monospace',
                                              fontWeight: FontWeight.bold,
                                              fontSize: 12,
                                              letterSpacing: 0.5,
                                            ),
                                          ),
                                          RailOSDepartmentBadge(
                                            department: task['department'] as String? ?? 'ENGG',
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        task['title'] as String? ?? 'Maintenance Task',
                                        style: const TextStyle(
                                          color: RailOSTokens.text_primary,
                                          fontSize: 14,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 10),
                                      Row(
                                        children: [
                                          Icon(
                                            isFullyVerified
                                                ? Icons.check_circle_outline
                                                : Icons.checklist,
                                            size: 15,
                                            color: isFullyVerified
                                                ? RailOSTokens.status_ok_fg
                                                : RailOSTokens.text_muted,
                                          ),
                                          const SizedBox(width: 5),
                                          Text(
                                            '${steps.length} Steps ($completedSteps Verified)',
                                            style: TextStyle(
                                              color: isFullyVerified
                                                  ? RailOSTokens.status_ok_text
                                                  : RailOSTokens.text_secondary,
                                              fontSize: 12,
                                              fontFamily: 'monospace',
                                            ),
                                          ),
                                          const Spacer(),
                                          const Icon(
                                            Icons.chevron_right,
                                            size: 16,
                                            color: RailOSTokens.text_muted,
                                          ),
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
