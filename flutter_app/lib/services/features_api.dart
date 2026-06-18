import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

String get _base => '${apiBaseUrl.replaceAll('/api', '')}/api/features';

class FeaturesApi {
  static Future<dynamic> get(String path) async {
    final res = await http.get(Uri.parse('$_base$path'));
    return jsonDecode(res.body);
  }

  static Future<dynamic> post(String path, [Map<String, dynamic>? body]) async {
    final res = await http.post(
      Uri.parse('$_base$path'),
      headers: {'Content-Type': 'application/json'},
      body: body != null ? jsonEncode(body) : null,
    );
    return jsonDecode(res.body);
  }

  static Future<dynamic> delete(String path) async {
    final res = await http.delete(Uri.parse('$_base$path'));
    return jsonDecode(res.body);
  }
}
