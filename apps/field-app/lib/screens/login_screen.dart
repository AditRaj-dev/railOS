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
    return Scaffold(
      backgroundColor: RailOSTokens.bg_darkRoot,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(RailOSTokens.spacingLg),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Logo mark
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: RailOSTokens.primary_railBlue,
                      borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                      border: Border.all(color: Colors.lightBlueAccent, width: 2),
                    ),
                    alignment: Alignment.center,
                    child: const Text(
                      'R',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingMd),

                  Text(
                    AppStrings.get('app_title'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingXs),

                  Text(
                    AppStrings.get('login_title'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: RailOSTokens.bg_lightBorder, fontSize: 14),
                  ),
                  const SizedBox(height: RailOSTokens.spacingXl),

                  // Language Switcher
                  Wrap(
                    alignment: WrapAlignment.center,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      const Icon(Icons.language, color: Colors.cyan, size: 18),
                      ChoiceChip(
                        label: const Text('English'),
                        selected: AppStrings.currentLanguage == 'en',
                        onSelected: (selected) {
                          if (selected) setState(() => AppStrings.currentLanguage = 'en');
                        },
                      ),
                      ChoiceChip(
                        label: const Text('हिन्दी (Hindi)'),
                        selected: AppStrings.currentLanguage == 'hi',
                        onSelected: (selected) {
                          if (selected) setState(() => AppStrings.currentLanguage = 'hi');
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: RailOSTokens.spacingLg),

                  // Employee ID
                  TextFormField(
                    controller: _empController,
                    style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
                    decoration: InputDecoration(
                      labelText: AppStrings.get('emp_id_hint'),
                      labelStyle: const TextStyle(color: Colors.white70),
                      prefixIcon: const Icon(Icons.badge, color: Colors.cyan),
                      filled: true,
                      fillColor: RailOSTokens.bg_darkSurface,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                        borderSide: const BorderSide(color: RailOSTokens.bg_darkBorder),
                      ),
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingMd),

                  // Password
                  TextFormField(
                    controller: _pwdController,
                    obscureText: true,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      labelText: AppStrings.get('password_hint'),
                      labelStyle: const TextStyle(color: Colors.white70),
                      prefixIcon: const Icon(Icons.lock, color: Colors.cyan),
                      filled: true,
                      fillColor: RailOSTokens.bg_darkSurface,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                        borderSide: const BorderSide(color: RailOSTokens.bg_darkBorder),
                      ),
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingLg),

                  if (_errorMessage != null) ...[
                    Container(
                      padding: const EdgeInsets.all(RailOSTokens.spacingSm),
                      decoration: BoxDecoration(
                        color: RailOSTokens.status_rejected_bg,
                        borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusSm),
                        border: Border.all(color: RailOSTokens.status_rejected_border),
                      ),
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: Colors.white, fontSize: 12),
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
                        backgroundColor: RailOSTokens.primary_railBlue,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(RailOSTokens.borderRadiusMd),
                        ),
                      ),
                      child: _isLoading
                          ? const SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : Text(
                              AppStrings.get('login_btn'),
                              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                            ),
                    ),
                  ),
                  const SizedBox(height: RailOSTokens.spacingMd),

                  // Offline notice
                  const Text(
                    '24-Hour Offline Entitlement Supported. Captured media is persisted locally before sync.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white54, fontSize: 11),
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
