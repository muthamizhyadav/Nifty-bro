import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/chat_message.dart';
import '../state/bot_state.dart';

class McpState extends ChangeNotifier {
  final List<ChatMessage> messages = [];
  bool loading = false;
  bool configured = false;
  String model = '';
  int toolsCount = 0;
  String? error;

  Future<void> fetchStatus() async {
    try {
      final res = await http.get(Uri.parse('$API_URL/mcp/status'));
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      configured = data['configured'] ?? false;
      model = data['model']?.toString() ?? '';
      toolsCount = data['tools_count'] ?? 0;
      error = null;
      notifyListeners();
    } catch (e) {
      error = e.toString();
      notifyListeners();
    }
  }

  Future<void> sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || loading) return;

    messages.add(ChatMessage(role: 'user', content: trimmed));
    loading = true;
    error = null;
    notifyListeners();

    try {
      final history = messages
          .where((m) => m.role == 'user' || m.role == 'assistant')
          .map((m) => m.toHistoryJson())
          .toList();
      // Exclude the message we just added from history sent to API
      if (history.isNotEmpty) history.removeLast();

      final res = await http.post(
        Uri.parse('$API_URL/mcp/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'message': trimmed, 'history': history}),
      );

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      if (res.statusCode >= 400) {
        throw Exception(data['detail'] ?? 'Request failed');
      }

      final reply = data['reply']?.toString() ?? 'No response';
      final toolCalls = data['tool_calls'] != null
          ? List<Map<String, dynamic>>.from(data['tool_calls'])
          : null;

      messages.add(ChatMessage(
        role: 'assistant',
        content: reply,
        toolCalls: toolCalls,
      ));
      configured = data['error'] != 'missing_api_key';
    } catch (e) {
      error = e.toString();
      messages.add(ChatMessage(
        role: 'assistant',
        content: 'Error: $e',
      ));
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void clearChat() {
    messages.clear();
    error = null;
    notifyListeners();
  }

  void addAssistantReply(String reply, {List<Map<String, dynamic>>? toolCalls}) {
    messages.add(ChatMessage(
      role: 'assistant',
      content: reply,
      toolCalls: toolCalls,
    ));
    notifyListeners();
  }
}
