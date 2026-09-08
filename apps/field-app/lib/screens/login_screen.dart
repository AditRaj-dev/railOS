import 'package:flutter/material.dart';
import '../l10n/app_strings.dart';
import '../services/api_client.dart';
import '../theme/railos_tokens.dart';

class LoginScreen extends StatefulWidget {
  final RailOSApiClient apiClient;
  final VoidCallback onLoginSuccess;

  const LoginScreen({
    super.key,
    required this.apiClient,
    required this.onLoginSuccess,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _empController = TextEditingController(text: 'EMP901');
  final _pwdController = TextEditingController(text: 'Field@123');
  bool _isLoading = false;
  String? _errorMessage;

  Future<void> _handleLogin() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await widget.apiClient.login(
        _empController.text.trim(),
        _pwdController.text,
      );
      widget.onLoginSuccess();
    } catch (e) {
      setState(() {
        _errorMessage = 'Authentication failed: ${e.toString().replaceAll('Exception:', '')}';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isHindi = AppStrings.currentLanguage == 'hi';

    return Scaffold(
      backgroundColor: RailOSTokens.bg_canvas,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: RailOSTokens.spacingLg,
              vertical: RailOSTokens.spacingXl,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // RailOS Logo & Header Mark
                  Center(
                    child: Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: RailOSTokens.bg_panel,
                        borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                        border: Border.all(color: RailOSTokens.border_default, width: 1),
                      ),
                      alignment: Alignment.center,
                      child: Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: RailOSTokens.accent.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                          border: Border.all(color: RailOSTokens.accent, width: 1.5),
                        ),
                        alignment: Alignment.center,
                        child: const Text(
                          'R',
                          style: TextStyle(
                            color: RailOSTokens.accent,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingMd),

                  Text(
                    AppStrings.get('app_title'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: RailOSTokens.text_primary,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.3,
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingXs),

                  Text(
                    AppStrings.get('login_title'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: RailOSTokens.text_secondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingLg),

                  // Language Switcher using Design Tokens
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    decoration: BoxDecoration(
                      color: RailOSTokens.bg_panel,
                      borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                      border: Border.all(color: RailOSTokens.border_default),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.language,
                          color: RailOSTokens.text_muted,
                          size: 16,
                        ),
                        const SizedBox(width: 8),
                        ChoiceChip(
                          label: const Text('English'),
                          selected: !isHindi,
                          selectedColor: RailOSTokens.bg_elevated,
                          backgroundColor: Colors.transparent,
                          labelStyle: TextStyle(
                            color: !isHindi ? RailOSTokens.accent : RailOSTokens.text_muted,
                            fontWeight: !isHindi ? FontWeight.bold : FontWeight.normal,
                            fontSize: 12,
                          ),
                          side: BorderSide(
                            color: !isHindi ? RailOSTokens.accent : RailOSTokens.border_subtle,
                          ),
                          onSelected: (selected) {
                            if (selected) setState(() => AppStrings.currentLanguage = 'en');
                          },
                        ),
                        const SizedBox(width: 8),
                        ChoiceChip(
                          label: const Text('हिन्दी (Hindi)'),
                          selected: isHindi,
                          selectedColor: RailOSTokens.bg_elevated,
                          backgroundColor: Colors.transparent,
                          labelStyle: TextStyle(
                            color: isHindi ? RailOSTokens.accent : RailOSTokens.text_muted,
                            fontWeight: isHindi ? FontWeight.bold : FontWeight.normal,
                            fontSize: 12,
                          ),
                          side: BorderSide(
                            color: isHindi ? RailOSTokens.accent : RailOSTokens.border_subtle,
                          ),
                          onSelected: (selected) {
                            if (selected) setState(() => AppStrings.currentLanguage = 'hi');
                          },
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingLg),

                  // Form Container
                  Container(
                    padding: const EdgeInsets.all(RailOSTokens.spacingLg),
                    decoration: BoxDecoration(
                      color: RailOSTokens.bg_panel,
                      borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                      border: Border.all(color: RailOSTokens.border_default),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Employee ID
                        TextFormField(
                          controller: _empController,
                          style: const TextStyle(
                            color: RailOSTokens.text_primary,
                            fontFamily: 'monospace',
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                          decoration: InputDecoration(
                            labelText: AppStrings.get('emp_id_hint'),
                            prefixIcon: const Icon(
                              Icons.badge_outlined,
                              color: RailOSTokens.text_muted,
                              size: 18,
                            ),
                          ),
                        ),
                        const SizedBox(height: RailOSTokens.spacingMd),

                        // Password
                        TextFormField(
                          controller: _pwdController,
                          obscureText: true,
                          style: const TextStyle(
                            color: RailOSTokens.text_primary,
                            fontSize: 14,
                          ),
                          decoration: InputDecoration(
                            labelText: AppStrings.get('password_hint'),
                            prefixIcon: const Icon(
                              Icons.lock_outline,
                              color: RailOSTokens.text_muted,
                              size: 18,
                            ),
                          ),
                        ),
                        const SizedBox(height: RailOSTokens.spacingLg),

                        if (_errorMessage != null) ...[
                          Container(
                            padding: const EdgeInsets.all(RailOSTokens.spacingSm),
                            decoration: BoxDecoration(
                              color: RailOSTokens.status_critical_bg,
                              borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                              border: Border.all(color: RailOSTokens.status_critical_border),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(
                                  Icons.error_outline,
                                  color: RailOSTokens.status_critical_fg,
                                  size: 16,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _errorMessage!,
                                    style: const TextStyle(
                                      color: RailOSTokens.status_critical_text,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: RailOSTokens.spacingMd),
                        ],

                        // Login Button with min 48dp touch target
                        SizedBox(
                          height: RailOSTokens.minTouchTargetDp,
                          child: ElevatedButton(
                            onPressed: _isLoading ? null : _handleLogin,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: RailOSTokens.accent,
                              foregroundColor: RailOSTokens.bg_canvas,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                              ),
                            ),
                            child: _isLoading
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: RailOSTokens.bg_canvas,
                                    ),
                                  )
                                : Text(
                                    AppStrings.get('login_btn'),
                                    style: const TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 0.3,
                                    ),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingMd),

                  // Offline notice with subtle border & icon
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: RailOSTokens.bg_surface,
                      borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                      border: Border.all(color: RailOSTokens.border_subtle),
                    ),
                    child: const Row(
                      children: [
                        Icon(
                          Icons.shield_outlined,
                          color: RailOSTokens.text_muted,
                          size: 16,
                        ),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '24-Hour Offline Entitlement Supported. All media proofs are encrypted and queued locally.',
                            style: TextStyle(
                              color: RailOSTokens.text_muted,
                              fontSize: 11,
                              height: 1.3,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
