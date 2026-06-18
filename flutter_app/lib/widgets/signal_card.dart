import 'package:flutter/material.dart';
import '../state/bot_state.dart';

// ─── Price header ─────────────────────────────────────────────────────
class PriceHeader extends StatelessWidget {
  final BotState state;
  const PriceHeader({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final price = state.currentPrice;
    final base = state.candles.isNotEmpty ? state.candles.first.open : 24380.0;
    final chg = price - base;
    final pct = base > 0 ? chg / base * 100 : 0;
    final isUp = chg >= 0;
    final color = isUp ? const Color(0xFF00D97E) : const Color(0xFFFF4757);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: const BoxDecoration(
        color: Color(0xFF0E1015),
        border: Border(bottom: BorderSide(color: Color(0xFF181C24))),
      ),
      child: Row(
        children: [
          const Text('NIFTY', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11)),
          const Text('AI', style: TextStyle(color: Color(0xFF00D97E), fontWeight: FontWeight.w800, fontSize: 11)),
          const SizedBox(width: 12),
          Text(price > 0 ? price.toStringAsFixed(2) : '—',
            style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(width: 8),
          Text(
            price > 0 ? '${isUp ? "+" : ""}${chg.toStringAsFixed(2)} (${pct.toStringAsFixed(2)}%)' : '',
            style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 10),
          ),
          const Spacer(),
          Container(
            width: 7, height: 7,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: state.connected ? const Color(0xFF00D97E)
                  : state.backendReachable ? const Color(0xFFF5A623)
                  : const Color(0xFFFF4757),
            ),
          ),
          const SizedBox(width: 6),
          Text(
            state.connected ? 'LIVE' : state.backendReachable ? 'WS OFF' : 'OFFLINE',
            style: TextStyle(
              color: state.connected ? const Color(0xFF00D97E)
                  : state.backendReachable ? const Color(0xFFF5A623)
                  : const Color(0xFFFF4757),
              fontFamily: 'monospace', fontSize: 9, letterSpacing: 0.8,
            )),
          const SizedBox(width: 8),
          Container(
            width: 7, height: 7,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: state.running ? const Color(0xFF00D97E) : const Color(0xFF4A4F62),
            ),
          ),
          const SizedBox(width: 6),
          Text(state.running ? 'RUNNING' : 'STOPPED',
            style: TextStyle(
              color: state.running ? const Color(0xFF00D97E) : const Color(0xFF4A4F62),
              fontFamily: 'monospace', fontSize: 9, letterSpacing: 0.8,
            )),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: state.toggleBot,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                border: Border.all(
                  color: state.running ? const Color(0xFFFF4757) : const Color(0xFF00D97E),
                ),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                state.running ? 'STOP' : 'START',
                style: TextStyle(
                  color: state.running ? const Color(0xFFFF4757) : const Color(0xFF00D97E),
                  fontFamily: 'monospace', fontSize: 9, fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Signal card ──────────────────────────────────────────────────────
class SignalCard extends StatelessWidget {
  final Map<String, dynamic>? signal;
  final String? statusMessage;
  final bool marketDataOk;
  const SignalCard({super.key, this.signal, this.statusMessage, this.marketDataOk = false});

  @override
  Widget build(BuildContext context) {
    if (signal == null) {
      final msg = statusMessage
          ?? (marketDataOk ? 'Waiting for next 15m candle close...' : 'No market data — reconnect Fyers in Settings');
      return _panel('AI SIGNAL', Container(
        padding: const EdgeInsets.all(20),
        alignment: Alignment.center,
        child: Text(msg,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: marketDataOk ? const Color(0xFF4A4F62) : const Color(0xFFF5A623),
            fontSize: 11,
          )),
      ));
    }

    final sig = signal!['signal'] ?? 'WAIT';
    final color = sig == 'LONG' ? const Color(0xFF00D97E)
                : sig == 'SHORT' ? const Color(0xFFFF4757)
                : const Color(0xFFF5A623);

    return _panel('AI SIGNAL', Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        border: Border.all(color: color.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(sig, style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 11, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(width: 10),
              Expanded(child: Text(signal!['title'] ?? '',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
            ],
          ),
          const SizedBox(height: 10),
          if (sig != 'WAIT') Row(
            children: [
              _level('ENTRY', signal!['entry_zone'], const Color(0xFF4DA6FF)),
              _level('SL', signal!['stop_loss'], const Color(0xFFFF4757)),
              _level('T2', signal!['target_2'], const Color(0xFF00D97E)),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Text('Confidence ', style: TextStyle(color: Color(0xFF4A4F62), fontFamily: 'monospace', fontSize: 9)),
              Expanded(
                child: Container(
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1A1D24),
                    borderRadius: BorderRadius.circular(2),
                  ),
                  child: FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: (signal!['confidence'] ?? 0) / 100,
                    child: Container(
                      decoration: BoxDecoration(
                        color: color,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              Text('${signal!['confidence'] ?? 0}%',
                style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 10)),
            ],
          ),
          const SizedBox(height: 10),
          Text(signal!['reasoning'] ?? '',
            style: const TextStyle(fontSize: 11, color: Color(0xFFA0A4B8), height: 1.5)),
        ],
      ),
    ));
  }

  Widget _level(String label, dynamic val, Color color) => Expanded(
    child: Container(
      margin: const EdgeInsets.symmetric(horizontal: 2),
      padding: const EdgeInsets.symmetric(vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF13161D),
        borderRadius: BorderRadius.circular(5),
      ),
      child: Column(
        children: [
          Text(label, style: const TextStyle(color: Color(0xFF4A4F62), fontFamily: 'monospace', fontSize: 8)),
          const SizedBox(height: 2),
          Text(val?.toString() ?? '—',
            style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 11, fontWeight: FontWeight.bold)),
        ],
      ),
    ),
  );
}

// ─── Stats row ─────────────────────────────────────────────────────────
class StatsRow extends StatelessWidget {
  final Map<String, dynamic> stats;
  const StatsRow({super.key, required this.stats});

  @override
  Widget build(BuildContext context) {
    final pnl = (stats['today_pnl'] ?? 0).toDouble();
    final wr = stats['win_rate'] ?? 0;
    final total = stats['total_trades'] ?? 0;
    return Row(
      children: [
        _stat("TODAY P&L", '${pnl >= 0 ? "+" : ""}₹${pnl.toStringAsFixed(0)}',
              pnl >= 0 ? const Color(0xFF00D97E) : const Color(0xFFFF4757)),
        const SizedBox(width: 8),
        _stat("WIN RATE", total > 0 ? '$wr%' : '—',
              wr is num && wr >= 60 ? const Color(0xFF00D97E) : const Color(0xFFF5A623)),
        const SizedBox(width: 8),
        _stat("TRADES", '$total', Colors.white),
      ],
    );
  }

  Widget _stat(String l, String v, Color c) => Expanded(
    child: Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1117),
        border: Border.all(color: const Color(0xFF1C2029)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Text(v, style: TextStyle(color: c, fontFamily: 'monospace', fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 3),
          Text(l, style: const TextStyle(color: Color(0xFF4A4F62), fontFamily: 'monospace', fontSize: 8, letterSpacing: 0.8)),
        ],
      ),
    ),
  );
}

// ─── Activity log ──────────────────────────────────────────────────────
class LogPanel extends StatelessWidget {
  final List<Map<String, String>> logs;
  const LogPanel({super.key, required this.logs});

  @override
  Widget build(BuildContext context) {
    return _panel('ACTIVITY LOG', Container(
      height: 160,
      padding: const EdgeInsets.all(10),
      child: logs.isEmpty
        ? const Center(child: Text('No activity yet', style: TextStyle(color: Color(0xFF4A4F62), fontSize: 10)))
        : ListView.builder(
            itemCount: logs.length,
            itemBuilder: (ctx, i) {
              final log = logs[i];
              final color = log['color'] == 'green' ? const Color(0xFF00D97E)
                          : log['color'] == 'red' ? const Color(0xFFFF4757)
                          : log['color'] == 'amber' ? const Color(0xFFF5A623)
                          : log['color'] == 'blue' ? const Color(0xFF4DA6FF)
                          : const Color(0xFF8A8E9C);
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    SizedBox(
                      width: 60,
                      child: Text(log['time'] ?? '',
                        style: const TextStyle(color: Color(0xFF4A4F62), fontFamily: 'monospace', fontSize: 9)),
                    ),
                    Expanded(
                      child: Text(log['msg'] ?? '',
                        style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 9)),
                    ),
                  ],
                ),
              );
            },
          ),
    ));
  }
}

// ─── Reusable panel ───────────────────────────────────────────────────
Widget _panel(String title, Widget child) => Container(
  decoration: BoxDecoration(
    color: const Color(0xFF0E1117),
    border: Border.all(color: const Color(0xFF1C2029)),
    borderRadius: BorderRadius.circular(8),
  ),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
        child: Text(title, style: const TextStyle(
          color: Color(0xFF4A4F62), fontFamily: 'monospace',
          fontSize: 9, letterSpacing: 1.2,
        )),
      ),
      child,
    ],
  ),
);