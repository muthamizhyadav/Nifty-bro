import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/mcp_state.dart';

class McpScreen extends StatefulWidget {
  const McpScreen({super.key});

  @override
  State<McpScreen> createState() => _McpScreenState();
}

class _McpScreenState extends State<McpScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  static const _quickPrompts = [
    "What's the bot status right now?",
    "Show today's trading stats",
    "Explain the latest signal",
    "Summarize recent trades",
    "What's the market context (VIX, PCR)?",
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<McpState>().fetchStatus();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send(String text) async {
    _controller.clear();
    await context.read<McpState>().sendMessage(text);
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Consumer<McpState>(
        builder: (ctx, mcp, _) {
          _scrollToBottom();
          return Column(
            children: [
              _StatusBar(mcp: mcp),
              Expanded(child: _MessageList(mcp: mcp, scrollController: _scrollController)),
              if (!mcp.configured) _ConfigWarning(),
              _QuickChips(onTap: _send, enabled: !mcp.loading),
              _InputBar(
                controller: _controller,
                loading: mcp.loading,
                onSend: () => _send(_controller.text),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _StatusBar extends StatelessWidget {
  final McpState mcp;
  const _StatusBar({required this.mcp});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: const BoxDecoration(
        color: Color(0xFF0A0C10),
        border: Border(bottom: BorderSide(color: Color(0xFF1C2029))),
      ),
      child: Row(
        children: [
          Icon(
            mcp.configured ? Icons.smart_toy : Icons.smart_toy_outlined,
            color: mcp.configured ? const Color(0xFF00D97E) : const Color(0xFFF5A623),
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Claude MCP Assistant',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                Text(
                  mcp.configured
                      ? '${mcp.toolsCount} tools · ${mcp.model}'
                      : 'API key not configured',
                  style: const TextStyle(color: Color(0xFF4A4F62), fontSize: 9),
                ),
              ],
            ),
          ),
          if (mcp.messages.isNotEmpty)
            GestureDetector(
              onTap: mcp.clearChat,
              child: const Icon(Icons.delete_outline, color: Color(0xFF4A4F62), size: 18),
            ),
        ],
      ),
    );
  }
}

class _ConfigWarning extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1408),
        border: Border.all(color: const Color(0xFFF5A623)),
        borderRadius: BorderRadius.circular(6),
      ),
      child: const Text(
        'Set ANTHROPIC_API_KEY in backend/.env and restart the server.',
        style: TextStyle(color: Color(0xFFF5A623), fontSize: 10),
      ),
    );
  }
}

class _QuickChips extends StatelessWidget {
  final void Function(String) onTap;
  final bool enabled;
  const _QuickChips({required this.onTap, required this.enabled});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        children: _McpScreenState._quickPrompts.map((p) => Padding(
          padding: const EdgeInsets.only(right: 6),
          child: ActionChip(
            label: Text(p, style: const TextStyle(fontSize: 9)),
            backgroundColor: const Color(0xFF13161D),
            side: const BorderSide(color: Color(0xFF1C2029)),
            onPressed: enabled ? () => onTap(p) : null,
          ),
        )).toList(),
      ),
    );
  }
}

class _MessageList extends StatelessWidget {
  final McpState mcp;
  final ScrollController scrollController;
  const _MessageList({required this.mcp, required this.scrollController});

  @override
  Widget build(BuildContext context) {
    if (mcp.messages.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Ask Claude about bot status, signals, trades,\nmarket context, or configuration.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Color(0xFF4A4F62), fontSize: 11, height: 1.5),
          ),
        ),
      );
    }

    return ListView.builder(
      controller: scrollController,
      padding: const EdgeInsets.all(12),
      itemCount: mcp.messages.length + (mcp.loading ? 1 : 0),
      itemBuilder: (ctx, i) {
        if (mcp.loading && i == mcp.messages.length) {
          return const _TypingIndicator();
        }
        final msg = mcp.messages[i];
        return _Bubble(message: msg);
      },
    );
  }
}

class _Bubble extends StatelessWidget {
  final dynamic message;
  const _Bubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF0D2B1F) : const Color(0xFF0E1117),
          border: Border.all(
            color: isUser ? const Color(0xff00d97e33) : const Color(0xFF1C2029),
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              isUser ? 'You' : 'Claude',
              style: TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w700,
                color: isUser ? const Color(0xFF00D97E) : const Color(0xFF4DA6FF),
              ),
            ),
            const SizedBox(height: 4),
            Text(message.content, style: const TextStyle(fontSize: 11, height: 1.45)),
            if (message.toolCalls != null && message.toolCalls!.isNotEmpty) ...[
              const SizedBox(height: 6),
              ...message.toolCalls!.map((t) => Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(
                  '🔧 ${t['name']}',
                  style: const TextStyle(color: Color(0xFF4A4F62), fontSize: 9),
                ),
              )),
            ],
          ],
        ),
      ),
    );
  }
}

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator();

  @override
  Widget build(BuildContext context) {
    return const Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: EdgeInsets.only(bottom: 10),
        child: Text('Claude is thinking...',
            style: TextStyle(color: Color(0xFF4A4F62), fontSize: 10, fontStyle: FontStyle.italic)),
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final bool loading;
  final VoidCallback onSend;
  const _InputBar({required this.controller, required this.loading, required this.onSend});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
      decoration: const BoxDecoration(
        color: Color(0xFF0A0C10),
        border: Border(top: BorderSide(color: Color(0xFF1C2029))),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              enabled: !loading,
              style: const TextStyle(fontSize: 12),
              maxLines: 3,
              minLines: 1,
              decoration: InputDecoration(
                hintText: 'Ask about trades, signals, market...',
                hintStyle: const TextStyle(color: Color(0xFF4A4F62), fontSize: 11),
                filled: true,
                fillColor: const Color(0xFF0E1117),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF1C2029)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: Color(0xFF1C2029)),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              onSubmitted: loading ? null : (_) => onSend(),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: loading ? null : onSend,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: loading ? const Color(0xFF1C2029) : const Color(0xFF00D97E),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                loading ? Icons.hourglass_empty : Icons.send,
                color: loading ? const Color(0xFF4A4F62) : Colors.black,
                size: 18,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
