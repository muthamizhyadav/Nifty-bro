import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

/// Backend connection settings.
///
/// Android (USB dev): run `adb reverse tcp:8000 tcp:8000` then uses 127.0.0.1
/// Android (Wi‑Fi only): set [_lanHost] to your Mac IP (ipconfig getifaddr en0)
const String _lanHost = '192.168.1.6';
const int _backendPort = 8000;

/// USB debugging: adb reverse makes phone's localhost reach Mac backend.
const bool _useLocalhostOnAndroid = false;

String get _host {
  if (kIsWeb) return 'localhost';
  if (!kIsWeb && Platform.isAndroid) {
    return _useLocalhostOnAndroid ? '127.0.0.1' : _lanHost;
  }
  if (!kIsWeb && Platform.isIOS) return _lanHost;
  return 'localhost';
}

String get apiBaseUrl => 'http://$_host:$_backendPort/api';
String get wsBaseUrl => 'ws://$_host:$_backendPort/ws';
