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
        const SnackBar(content: Text('Please enter hazard description')),
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
            backgroundColor: RailOSTokens.bg_darkSurface,
            title: const Text('Emergency Report Dispatched', style: TextStyle(color: Colors.white)),
            content: Text(
              'Report $reportId has been transmitted to Control Center with highest operational priority.',
              style: const TextStyle(color: Colors.white70),
            ),
            actions: [
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: RailOSTokens.primary_safetyRed),
                onPressed: () {
                  Navigator.pop(ctx);
                  Navigator.pop(context);
                },
                child: const Text('Return to Work', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to submit report: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: RailOSTokens.bg_darkRoot,
      appBar: AppBar(
        backgroundColor: RailOSTokens.primary_safetyRed,
        title: Text(
          AppStrings.get('emergency_btn'),
          style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(RailOSTokens.spacingMd),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Notice
              Container(
                padding: const EdgeInsets.all(RailOSTokens.spacingSm),
                decoration: BoxDecoration(
                  color: RailOSTokens.primary_safetyRed.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                  border: Border.all(color: RailOSTokens.primary_safetyRed),
                ),
                child: const Text(
                  'NOTICE: Emergency report transmits immediately to Divisional Control Center. '
                  'This app never authorizes possessions, isolations, train movements, or block extensions.',
                  style: TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
              const SizedBox(height: RailOSTokens.spacingMd),

              // Section & KM
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _sectionController,
                      style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
                      decoration: InputDecoration(
                        labelText: 'Section Code',
                        labelStyle: const TextStyle(color: Colors.white70),
                        filled: true,
                        fillColor: RailOSTokens.bg_darkSurface,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: RailOSTokens.spacingSm),
                  Expanded(
                    child: TextFormField(
                      controller: _kmController,
                      style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
                      decoration: InputDecoration(
                        labelText: 'KM / Telegraph Post',
                        labelStyle: const TextStyle(color: Colors.white70),
                        filled: true,
                        fillColor: RailOSTokens.bg_darkSurface,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: RailOSTokens.spacingMd),

              // Severity Dropdown
              DropdownButtonFormField<String>(
                value: _selectedSeverity,
                dropdownColor: RailOSTokens.bg_darkSurface,
                style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
                decoration: InputDecoration(
                  labelText: 'Defect / Hazard Severity',
                  labelStyle: const TextStyle(color: Colors.white70),
                  filled: true,
                  fillColor: RailOSTokens.bg_darkSurface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                  ),
                ),
                items: _severities
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: (val) => setState(() => _selectedSeverity = val!),
              ),
              const SizedBox(height: RailOSTokens.spacingMd),

              // Hazard Type Dropdown
              DropdownButtonFormField<String>(
                value: _selectedHazard,
                dropdownColor: RailOSTokens.bg_darkSurface,
                style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
                decoration: InputDecoration(
                  labelText: 'Hazard Classification',
                  labelStyle: const TextStyle(color: Colors.white70),
                  filled: true,
                  fillColor: RailOSTokens.bg_darkSurface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                  ),
                ),
                items: _hazards
                    .map((h) => DropdownMenuItem(value: h, child: Text(h)))
                    .toList(),
                onChanged: (val) => setState(() => _selectedHazard = val!),
              ),
              const SizedBox(height: RailOSTokens.spacingMd),

              // Description
              TextFormField(
                controller: _descController,
                style: const TextStyle(color: Colors.white),
                maxLines: 4,
                decoration: InputDecoration(
                  labelText: 'Field Observation & Hazard Details',
                  labelStyle: const TextStyle(color: Colors.white70),
                  hintText: 'Describe physical location, track condition, clearance impact, and immediate safety actions taken...',
                  hintStyle: const TextStyle(color: Colors.white30),
                  filled: true,
                  fillColor: RailOSTokens.bg_darkSurface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                  ),
                ),
              ),
              const SizedBox(height: RailOSTokens.spacingLg),

              // Submit Button
              SizedBox(
                height: RailOSTokens.minTouchTargetDp,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.send),
                  label: _isSubmitting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : const Text(
                          'Transmit Immediate Emergency Report',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                        ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: RailOSTokens.primary_safetyRed,
                    foregroundColor: Colors.white,
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
