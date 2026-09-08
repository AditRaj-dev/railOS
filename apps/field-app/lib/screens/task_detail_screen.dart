import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../models/evidence_models.dart';
import '../services/api_client.dart';
import '../theme/railos_tokens.dart';
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
    final allCompleted = _steps.every((s) => s.status == WorkExecutionStatus.completed);

    return Scaffold(
      backgroundColor: RailOSTokens.bg_darkRoot,
      appBar: AppBar(
        backgroundColor: RailOSTokens.bg_darkSurface,
        title: Text(taskId, style: const TextStyle(color: Colors.white, fontFamily: 'monospace')),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Task Header Details
            Container(
              padding: const EdgeInsets.all(RailOSTokens.spacingMd),
              color: RailOSTokens.bg_darkSurface,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(Icons.location_on, size: 14, color: Colors.cyan),
                      const SizedBox(width: 4),
                      Text(
                        'Corridor: ${widget.task['corridorId'] ?? 'GZB-ALJN'}',
                        style: const TextStyle(color: Colors.white70, fontSize: 12),
                      ),
                      const Spacer(),
                      Text(
                        'Target Radius: ${RailOSTokens.defaultTaskRadiusMeters.toInt()}m',
                        style: const TextStyle(color: Colors.white54, fontSize: 12),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: RailOSTokens.spacingSm),

            // Macro Steps Header
            Padding(
              padding: const EdgeInsets.all(RailOSTokens.spacingMd),
              child: Row(
                children: [
                  const Icon(Icons.format_list_numbered, color: Colors.cyan, size: 20),
                  const SizedBox(width: 8),
                  const Text(
                    'Ordered Macro Steps & Evidence',
                    style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),

            // Steps List
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: RailOSTokens.spacingMd),
                itemCount: _steps.length,
                separatorBuilder: (_, __) => const SizedBox(height: RailOSTokens.spacingSm),
                itemBuilder: (ctx, i) {
                  final step = _steps[i];
                  final isPhoto = step.requiresPhoto;
                  final isDone = step.status == WorkExecutionStatus.completed;

                  return Card(
                    color: RailOSTokens.bg_darkSurface,
                    shape: RoundedRectangleBorder(
                      side: BorderSide(
                        color: isDone
                            ? RailOSTokens.status_verified_border
                            : RailOSTokens.bg_darkBorder,
                        width: isDone ? 1.5 : 1.0,
                      ),
                      borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(RailOSTokens.spacingMd),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                radius: 12,
                                backgroundColor: isDone
                                    ? RailOSTokens.status_verified_bg
                                    : RailOSTokens.primary_railBlue,
                                child: Text(
                                  '${step.stepIndex}',
                                  style: TextStyle(
                                    color: isDone ? Colors.greenAccent : Colors.white,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  step.title,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              if (isDone)
                                const Icon(Icons.check_circle, color: Colors.greenAccent, size: 18),
                            ],
                          ),
                          if (step.description.isNotEmpty) ...[
                            const SizedBox(height: 6),
                            Text(
                              step.description,
                              style: const TextStyle(color: Colors.white60, fontSize: 12),
                            ),
                          ],
                          const SizedBox(height: 12),

                          // Action button for step (live photo or 90s video)
                          SizedBox(
                            width: double.infinity,
                            height: RailOSTokens.minTouchTargetDp,
                            child: ElevatedButton.icon(
                              icon: Icon(
                                isPhoto ? Icons.camera_alt : Icons.videocam,
                                size: 18,
                              ),
                              label: Text(
                                isDone
                                    ? 'Retake Proof'
                                    : (isPhoto
                                        ? AppStrings.get('capture_photo')
                                        : AppStrings.get('capture_video')),
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                              ),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: isDone
                                    ? Colors.blueGrey.shade800
                                    : (isPhoto
                                        ? RailOSTokens.primary_railBlue
                                        : Colors.purple.shade700),
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
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
                padding: const EdgeInsets.all(RailOSTokens.spacingMd),
                color: RailOSTokens.status_verified_bg,
                child: Row(
                  children: [
                    const Icon(Icons.verified, color: Colors.greenAccent),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Text(
                        'All Macro Steps & Final Video Captured and Verified!',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
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
