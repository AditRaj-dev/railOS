import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/evidence_models.dart';
import '../services/api_client.dart';
import '../theme/railos_tokens.dart';
import '../theme/railos_widgets.dart';
import 'capture_screen.dart';

class TaskDetailScreen extends StatefulWidget {
  final Map<String, dynamic> task;
  final List<WorkStep> steps;
  final RailOSApiClient apiClient;

  const TaskDetailScreen({
    super.key,
    required this.task,
    required this.steps,
    required this.apiClient,
  });

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  late List<WorkStep> _steps;

  @override
  void initState() {
    super.initState();
    _steps = widget.steps;
  }

  void _openCapture(WorkStep step) async {
    final result = await Navigator.push<CapturedEvidence>(
      context,
      MaterialPageRoute(
        builder: (_) => CaptureScreen(
          task: widget.task,
          step: step,
          apiClient: widget.apiClient,
        ),
      ),
    );

    if (result != null) {
      setState(() {
        step.status = result.status == EvidenceStatus.verified
            ? WorkExecutionStatus.completed
            : WorkExecutionStatus.completedPendingEvidence;
        step.evidenceId = result.evidenceId;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final taskId = widget.task['taskId'] as String? ?? '';
    final title = widget.task['title'] as String? ?? '';
    final department = widget.task['department'] as String? ?? 'ENGG';
    final allCompleted =
        _steps.isNotEmpty &&
        _steps.every((s) => s.status == WorkExecutionStatus.completed);

    return Scaffold(
      backgroundColor: RailOSTokens.bg_canvas,
      appBar: AppBar(
        backgroundColor: RailOSTokens.bg_surface,
        title: Text(
          taskId,
          style: const TextStyle(
            color: RailOSTokens.text_primary,
            fontFamily: 'monospace',
            fontWeight: FontWeight.bold,
            fontSize: 15,
          ),
        ),
        iconTheme: const IconThemeData(color: RailOSTokens.text_secondary),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Task Header Details Panel
            Container(
              padding: const EdgeInsets.all(RailOSTokens.spacingMd),
              decoration: const BoxDecoration(
                color: RailOSTokens.bg_surface,
                border: Border(
                  bottom: BorderSide(
                    color: RailOSTokens.border_default,
                    width: 1,
                  ),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            color: RailOSTokens.text_primary,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      RailOSDepartmentBadge(department: department),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Icon(
                        Icons.place_outlined,
                        size: 15,
                        color: RailOSTokens.text_muted,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Corridor: ${widget.task['corridorId'] ?? 'GZB-ALJN'}',
                        style: const TextStyle(
                          color: RailOSTokens.text_secondary,
                          fontFamily: 'monospace',
                          fontSize: 12,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        'Target Radius: ${RailOSTokens.defaultTaskRadiusMeters.toInt()}m',
                        style: const TextStyle(
                          color: RailOSTokens.text_muted,
                          fontFamily: 'monospace',
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Macro Steps Header
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: RailOSTokens.spacingMd,
                vertical: RailOSTokens.spacingSm,
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.format_list_numbered,
                    color: RailOSTokens.text_secondary,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'Ordered Macro Steps & Evidence',
                    style: TextStyle(
                      color: RailOSTokens.text_primary,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.2,
                    ),
                  ),
                ],
              ),
            ),

            // Steps List
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(
                  horizontal: RailOSTokens.spacingMd,
                  vertical: RailOSTokens.spacingXs,
                ),
                itemCount: _steps.length,
                separatorBuilder: (_, _) =>
                    const SizedBox(height: RailOSTokens.spacingSm),
                itemBuilder: (ctx, i) {
                  final step = _steps[i];
                  final isPhoto = step.requiresPhoto;
                  final isDone = step.status == WorkExecutionStatus.completed;

                  return Container(
                    decoration: BoxDecoration(
                      color: RailOSTokens.bg_panel,
                      borderRadius: BorderRadius.circular(
                        RailOSTokens.borderRadiusMd,
                      ),
                      border: Border.all(
                        color: isDone
                            ? RailOSTokens.status_ok_border
                            : RailOSTokens.border_default,
                        width: 1,
                      ),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(RailOSTokens.spacingMd),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 24,
                                height: 24,
                                decoration: BoxDecoration(
                                  color: isDone
                                      ? RailOSTokens.status_ok_bg
                                      : RailOSTokens.bg_elevated,
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color: isDone
                                        ? RailOSTokens.status_ok_border
                                        : RailOSTokens.border_strong,
                                    width: 1,
                                  ),
                                ),
                                alignment: Alignment.center,
                                child: Text(
                                  '${step.stepIndex}',
                                  style: TextStyle(
                                    color: isDone
                                        ? RailOSTokens.status_ok_fg
                                        : RailOSTokens.accent,
                                    fontSize: 11,
                                    fontFamily: 'monospace',
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  step.title,
                                  style: const TextStyle(
                                    color: RailOSTokens.text_primary,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              if (isDone)
                                const RailOSStatusChip(
                                  label: 'Verified',
                                  status: RailOSStatus.ok,
                                  compact: true,
                                ),
                            ],
                          ),
                          if (step.description.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Text(
                              step.description,
                              style: const TextStyle(
                                color: RailOSTokens.text_secondary,
                                fontSize: 12,
                                height: 1.4,
                              ),
                            ),
                          ],
                          const SizedBox(height: 12),

                          // Action button for step (live photo or video)
                          SizedBox(
                            width: double.infinity,
                            height: RailOSTokens.minTouchTargetDp,
                            child: isDone
                                ? OutlinedButton.icon(
                                    icon: const Icon(Icons.refresh, size: 16),
                                    label: const Text('Retake Proof'),
                                    style: OutlinedButton.styleFrom(
                                      foregroundColor:
                                          RailOSTokens.text_secondary,
                                      side: const BorderSide(
                                        color: RailOSTokens.border_default,
                                      ),
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(
                                          RailOSTokens.borderRadiusSm,
                                        ),
                                      ),
                                    ),
                                    onPressed: () => _openCapture(step),
                                  )
                                : ElevatedButton.icon(
                                    icon: Icon(
                                      isPhoto
                                          ? Icons.camera_alt_outlined
                                          : Icons.videocam_outlined,
                                      size: 18,
                                    ),
                                    label: Text(
                                      isPhoto
                                          ? AppStrings.get('capture_photo')
                                          : AppStrings.get('capture_video'),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                      ),
                                    ),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: RailOSTokens.accent,
                                      foregroundColor: RailOSTokens.bg_canvas,
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(
                                          RailOSTokens.borderRadiusSm,
                                        ),
                                      ),
                                    ),
                                    onPressed: () => _openCapture(step),
                                  ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

            // Completion Banner
            if (allCompleted)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: RailOSTokens.spacingMd,
                  vertical: 12,
                ),
                decoration: const BoxDecoration(
                  color: RailOSTokens.status_ok_bg,
                  border: Border(
                    top: BorderSide(
                      color: RailOSTokens.status_ok_border,
                      width: 1,
                    ),
                  ),
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      color: RailOSTokens.status_ok_fg,
                      size: 20,
                    ),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'All Macro Steps & Final Video Captured and Verified!',
                        style: TextStyle(
                          color: RailOSTokens.status_ok_text,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
