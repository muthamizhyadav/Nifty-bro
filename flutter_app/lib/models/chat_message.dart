class ChatMessage {
  final String role; // 'user' | 'assistant'
  final String content;
  final DateTime time;
  final List<Map<String, dynamic>>? toolCalls;

  ChatMessage({
    required this.role,
    required this.content,
    DateTime? time,
    this.toolCalls,
  }) : time = time ?? DateTime.now();

  Map<String, dynamic> toHistoryJson() => {
    'role': role,
    'content': content,
  };
}
