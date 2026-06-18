import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/bot_state.dart';
import 'package:url_launcher/url_launcher.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Consumer<BotState>(
        builder: (ctx, state, _) => ListView(
        padding: const EdgeInsets.all(14),
        children: [
          _connectCard(state),
          _card('Claude MCP Assistant', [
            _info('AI tab: chat with Claude using live bot data'),
            _info('MCP tools: status, trades, signals, candles, market'),
            _info('API key: backend/.env → ANTHROPIC_API_KEY'),
            _info('MCP HTTP endpoint: http://localhost:8000/mcp-trading/mcp'),
          ]),
          _card('Backend connection', [
            _field('API URL', 'http://localhost:8000', editable: false),
            _field('WebSocket URL', 'ws://localhost:8000/ws', editable: false),
          ]),
          _card('Trading config (set in backend/config.py)', [
            _field('Capital', '₹100,000'),
            _field('Risk per trade', '1.0%'),
            _field('Max trades/day', '3'),
            _field('Daily loss limit', '2.5%'),
            _field('Min confidence', '75%'),
            _field('Min R:R', '1:1.5'),
            _field('Mode', 'PAPER TRADING'),
          ]),
          _card('Fyers API — mobile login', [
            _info('Add redirect URL in Fyers dashboard:'),
            _info('http://192.168.1.2:8000/api/auth/callback'),
            _info('Phone + Mac must be on same Wi‑Fi'),
            _info('USB dev: run adb reverse tcp:8000 tcp:8000'),
          ]),
          _card('Fyers API status', [
            _field('App ID', 'Configured'),
            _field('Access Token', 'Valid'),
            _field('Token expires', 'Daily — reconnect each morning'),
          ]),
          _card('How to update config', [
            _info('1. Edit backend/config.py'),
            _info('2. Restart backend: python bot.py'),
            _info('3. Refresh Fyers token: python fyers_auth.py'),
          ]),
        ],
      ),
      ),
    );
  }

  Widget _connectCard(BotState state) => Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: const Color(0xFF0E1117),
      border: Border.all(color: state.authenticated ? const Color(0xFF00D97E) : const Color(0xFFF5A623)),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Icon(state.authenticated ? Icons.check_circle : Icons.warning_amber,
               color: state.authenticated ? const Color(0xFF00D97E) : const Color(0xFFF5A623), size: 18),
          const SizedBox(width: 8),
          Text(state.authenticated ? 'Fyers Connected' : 'Fyers Not Connected',
               style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
        ]),
        const SizedBox(height: 10),
        // Connect / Reconnect — ALWAYS available (tokens expire daily)
        GestureDetector(
          onTap: state.connectFyers,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 10),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: const Color(0xFF00D97E),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(state.authenticated ? 'Reconnect Fyers' : 'Connect Fyers',
              style: const TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 12)),
          ),
        ),
        if (state.authenticated) const SizedBox(height: 8),
        if (state.authenticated)
          GestureDetector(
            onTap: state.disconnectFyers,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                border: Border.all(color: const Color(0xFFFF4757)),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Text('Disconnect / Logout',
                style: TextStyle(color: Color(0xFFFF4757), fontWeight: FontWeight.bold, fontSize: 12)),
            ),
          ),
        if (state.authUrl != null) Padding(
          padding: const EdgeInsets.only(top: 10),
          child: GestureDetector(
            onTap: () async {
              final uri = Uri.parse(state.authUrl!);
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri, webOnlyWindowName: '_blank', mode: LaunchMode.externalApplication);
              }
            },
            child: Text(state.authUrl!,
              style: const TextStyle(color: Color(0xFF4DA6FF), fontSize: 10, decoration: TextDecoration.underline)),
          ),
        ),
        if (state.authUrl != null) const Padding(
          padding: EdgeInsets.only(top: 6),
          child: Text('Open this link, login, and the bot connects automatically.',
            style: TextStyle(color: Color(0xFF4A4F62), fontSize: 9)),
        ),
      ],
    ),
  );

  Widget _card(String title, List<Widget> children) => Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: const Color(0xFF0E1117),
      border: Border.all(color: const Color(0xFF1C2029)),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        ...children,
      ],
    ),
  );

  Widget _field(String label, String value, {bool editable = true}) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFFA0A4B8), fontFamily: 'monospace', fontSize: 11)),
        Text(value, style: TextStyle(
          color: editable ? Colors.white : const Color(0xFF4A4F62),
          fontFamily: 'monospace', fontSize: 11,
        )),
      ],
    ),
  );

  Widget _info(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 6),
    child: Text(text, style: const TextStyle(color: Color(0xFFA0A4B8), fontFamily: 'monospace', fontSize: 11)),
  );
}