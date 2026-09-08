class AppStrings {
  static String currentLanguage = 'en'; // 'en' or 'hi'

  static const Map<String, Map<String, String>> _localized = {
    'en': {
      'app_title': 'RailOS Field Evidence',
      'login_title': 'Field Supervisor Login',
      'emp_id_hint': 'Employee ID (e.g. EMP901)',
      'password_hint': 'Enter Password',
      'login_btn': 'Authenticate & Sync',
      'assigned_tasks': 'Assigned Work Tasks',
      'emergency_btn': 'Emergency Report',
      'capture_photo': 'Capture Step Photo',
      'capture_video': 'Record Completion Video',
      'step_status_ready': 'Ready to Capture',
      'step_status_completed': 'Verified & Completed',
      'step_status_flagged': 'Flagged Review',
      'location_fresh': 'GPS Fix Fresh',
      'location_stale': 'GPS Stale (>30s)',
      'within_radius': 'Within 100m Radius',
      'outside_radius': 'Outside Radius Exception',
      'exception_reason_prompt': 'Enter Mandatory Operational Reason for Exception',
      'submit_evidence': 'Process & Submit Evidence',
      'retake_btn': 'Retake Media',
      'evidence_strip_preview': 'RailOS Evidence Strip',
      'settings_lang': 'Language / भाषा',
      'sync_status': 'Offline Queue: {count} pending',
    },
    'hi': {
      'app_title': 'रेलोस फील्ड साक्ष्य (RailOS)',
      'login_title': 'फील्ड सुपरवाइजर लॉगिन',
      'emp_id_hint': 'कर्मचारी आईडी (जैसे EMP901)',
      'password_hint': 'पासवर्ड दर्ज करें',
      'login_btn': 'प्रमाणित करें एवं सिंक करें',
      'assigned_tasks': 'आवंटित कार्य (Tasks)',
      'emergency_btn': 'आपातकालीन रिपोर्ट',
      'capture_photo': 'चरण का लाइव फोटो लें',
      'capture_video': 'समापन वीडियो रिकॉर्ड करें (<=90s)',
      'step_status_ready': 'कैप्चर के लिए तैयार',
      'step_status_completed': 'सत्यापित एवं पूर्ण',
      'step_status_flagged': 'समीक्षाधीन अपवाद',
      'location_fresh': 'जीपीएस स्थिति ताज़ा (Fresh)',
      'location_stale': 'जीपीएस पुराना (>30s)',
      'within_radius': '100 मीटर दायरे के भीतर',
      'outside_radius': 'कार्य दायरे से बाहर (Exception)',
      'exception_reason_prompt': 'अपवाद का अनिवार्य परिचालन कारण दर्ज करें',
      'submit_evidence': 'साक्ष्य प्रोसेस एवं सबमिट करें',
      'retake_btn': 'पुनः फोटो/वीडियो लें',
      'evidence_strip_preview': 'रेलोस साक्ष्य पट्टी (Evidence Strip)',
      'settings_lang': 'Language / भाषा बदलें',
      'sync_status': 'ऑफलाइन कतार: {count} लंबित',
    },
  };

  static String get(String key) {
    return _localized[currentLanguage]?[key] ?? _localized['en']?[key] ?? key;
  }
}
