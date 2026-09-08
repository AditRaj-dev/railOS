import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../services/api_client.dart';
import '../theme/railos_tokens.dart';

class EmergencyScreen extends StatefulWidget {
  final RailOSApiClient apiClient;

  const EmergencyScreen({super.key, required this.apiClient});

  @override
  State<EmergencyScreen> createState() => _EmergencyScreenState();
}

class _EmergencyScreenState extends State<EmergencyScreen> {
  final _sectionController = TextEditingController(text: 'SEC_KRJ_SMQ');
  final _kmController = TextEditingController(text: 'KM 122/4');
  final _descController = TextEditingController();
  String _selectedSeverity = 'IMR';
  String _selectedHazard = 'FRACTURED_RAIL';
  bool _isSubmitting = false;

  final List<String> _severities = [
    'IMR',
    'IMRW',
    'OBS',
    'OMS_PEAK_HIGH',
    'POINT_SLACK_DETECTION',
    'OHE_DROPPING_FAULT',
  ];

  final List<String> _hazards = [
    'FRACTURED_RAIL',
    'WELD_FAILURE',
    'TRACK_CIRCUIT_BOND_CUT',
    'OHE_CATENARY_DROP',
    'TRACK_ALIGNMENT_SKEW',
    'BALLAST_WASHOUT',
  ];

  Future<void> _submitReport() async {
    if (_descController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter hazard description'),
          backgroundColor: RailOSTokens.status_caution_bg,
        ),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final reportId = 'EMERG-${DateTime.now().millisecondsSinceEpoch}';
      await widget.apiClient.submitEmergencyReport(
        reportId: reportId,
        sectionCode: _sectionController.text.trim(),
        kmPost: _kmController.text.trim(),
        latitude: 28.6139,
        longitude: 77.2090,
        severity: _selectedSeverity,
        hazardType: _selectedHazard,
        description: _descController.text.trim(),
      );

      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: RailOSTokens.bg_surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
              side: const BorderSide(color: RailOSTokens.border_default),
            ),
            title: const Row(
              children: [
                Icon(
                  Icons.check_circle_outline,
                  color: RailOSTokens.status_ok_fg,
                  size: 20,
                ),
                SizedBox(width: 8),
                Text(
                  'Emergency Transmitted',
                  style: TextStyle(
                    color: RailOSTokens.text_primary,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            content: Text(
              'Report $reportId has been transmitted to Divisional Control Center with highest operational priority.',
              style: const TextStyle(
                color: RailOSTokens.text_secondary,
                fontSize: 13,
                height: 1.4,
              ),
            ),
            actions: [
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: RailOSTokens.accent,
                  foregroundColor: RailOSTokens.bg_canvas,
                ),
                onPressed: () {
                  Navigator.pop(ctx);
                  Navigator.pop(context);
                },
                child: const Text('Return to Dashboard'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to submit report: $e'),
            backgroundColor: RailOSTokens.status_critical_bg,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: RailOSTokens.bg_canvas,
      appBar: AppBar(
        backgroundColor: RailOSTokens.bg_surface,
        title: Row(
          children: [
            const Icon(
              Icons.warning_amber_rounded,
              color: RailOSTokens.status_critical_fg,
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              AppStrings.get('emergency_btn'),
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 15,
                color: RailOSTokens.text_primary,
                letterSpacing: 0.2,
              ),
            ),
          ],
        ),
        iconTheme: const IconThemeData(color: RailOSTokens.text_secondary),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(RailOSTokens.spacingMd),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Notice banner complying with design tokens
              Container(
                padding: const EdgeInsets.all(RailOSTokens.spacingSm),
                decoration: BoxDecoration(
                  color: RailOSTokens.status_critical_bg,
                  borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                  border: Border.all(color: RailOSTokens.status_critical_border),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.shield_outlined,
                      color: RailOSTokens.status_critical_fg,
                      size: 16,
                    ),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'NOTICE: Emergency report transmits immediately to Divisional Control Center. '
                        'This app never authorizes possessions, isolations, train movements, or block extensions.',
                        style: TextStyle(
                          color: RailOSTokens.status_critical_text,
                          fontSize: 12,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: RailOSTokens.spacingMd),

              // Form Container Panel
              Container(
                padding: const EdgeInsets.all(RailOSTokens.spacingMd),
                decoration: BoxDecoration(
                  color: RailOSTokens.bg_panel,
                  borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                  border: Border.all(color: RailOSTokens.border_default),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Section & KM
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _sectionController,
                            style: const TextStyle(
                              color: RailOSTokens.text_primary,
                              fontFamily: 'monospace',
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                            decoration: const InputDecoration(
                              labelText: 'Section Code',
                            ),
                          ),
                        ),
                        const SizedBox(width: RailOSTokens.spacingSm),
                        Expanded(
                          child: TextFormField(
                            controller: _kmController,
                            style: const TextStyle(
                              color: RailOSTokens.text_primary,
                              fontFamily: 'monospace',
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                            decoration: const InputDecoration(
                              labelText: 'KM / Telegraph Post',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: RailOSTokens.spacingMd),

                    // Severity Dropdown
                    DropdownButtonFormField<String>(
                      initialValue: _selectedSeverity,
                      dropdownColor: RailOSTokens.bg_surface,
                      style: const TextStyle(
                        color: RailOSTokens.text_primary,
                        fontFamily: 'monospace',
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                      decoration: const InputDecoration(
                        labelText: 'Defect / Hazard Severity',
                      ),
                      items: _severities
                          .map(
                            (s) => DropdownMenuItem(
                              value: s,
                              child: Text(s),
                            ),
                          )
                          .toList(),
                      onChanged: (val) => setState(() => _selectedSeverity = val!),
                    ),
                    const SizedBox(height: RailOSTokens.spacingMd),

                    // Hazard Type Dropdown
                    DropdownButtonFormField<String>(
                      initialValue: _selectedHazard,
                      dropdownColor: RailOSTokens.bg_surface,
                      style: const TextStyle(
                        color: RailOSTokens.text_primary,
                        fontFamily: 'monospace',
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                      decoration: const InputDecoration(
                        labelText: 'Hazard Classification',
                      ),
                      items: _hazards
                          .map(
                            (h) => DropdownMenuItem(
                              value: h,
                              child: Text(h),
                            ),
                          )
                          .toList(),
                      onChanged: (val) => setState(() => _selectedHazard = val!),
                    ),
                    const SizedBox(height: RailOSTokens.spacingMd),

                    // Description
                    TextFormField(
                      controller: _descController,
                      style: const TextStyle(color: RailOSTokens.text_primary, fontSize: 13),
                      maxLines: 4,
                      decoration: const InputDecoration(
                        labelText: 'Field Observation & Hazard Details',
                        hintText:
                            'Describe physical location, track condition, clearance impact, and immediate safety actions taken...',
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: RailOSTokens.spacingLg),

              // Submit Button
              SizedBox(
                height: RailOSTokens.minTouchTargetDp,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.send_outlined, size: 18),
                  label: _isSubmitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            color: RailOSTokens.status_critical_text,
                            strokeWidth: 2,
                          ),
                        )
                      : const Text(
                          'Transmit Immediate Emergency Report',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                            letterSpacing: 0.3,
                          ),
                        ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: RailOSTokens.status_critical_bg,
                    foregroundColor: RailOSTokens.status_critical_text,
                    side: const BorderSide(color: RailOSTokens.status_critical_border),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                    ),
                  ),
                  onPressed: _isSubmitting ? null : _submitReport,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
