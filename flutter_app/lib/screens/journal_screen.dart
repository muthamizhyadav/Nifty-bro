import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/bot_state.dart';

class JournalScreen extends StatelessWidget {
  const JournalScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Consumer<BotState>(
        builder: (ctx, state, _) {
          final s = state.stats;
          return Column(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                color: const Color(0xFF0A0C10),
                child: GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  childAspectRatio: 3,
                  mainAxisSpacing: 8,
                  crossAxisSpacing: 8,
                  children: [
                    _stat('TOTAL TRADES', '${s['total_trades'] ?? 0}', Colors.white),
                    _stat('WIN RATE', '${s['win_rate'] ?? 0}%', const Color(0xFFF5A623)),
                    _stat('WINS', '${s['wins'] ?? 0}', const Color(0xFF00D97E)),
                    _stat('LOSSES', '${s['losses'] ?? 0}', const Color(0xFFFF4757)),
                  ],
                ),
              ),
              Expanded(
                child: state.trades.isEmpty
                  ? const Center(child: Text('No trades yet',
                      style: TextStyle(color: Color(0xFF4A4F62), fontFamily: 'monospace', fontSize: 11)))
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: state.trades.length,
                      itemBuilder: (ctx, i) {
                        final t = state.trades[i];
                        final pnl = (t['pnl'] ?? 0).toDouble();
                        final win = pnl > 0;
                        final color = win ? const Color(0xFF00D97E) : const Color(0xFFFF4757);
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF0E1117),
                            border: Border.all(color: color.withOpacity(0.3)),
                            borderRadius: BorderRadius.circular(7),
                          ),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: color.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(3),
                                ),
                                child: Text(t['direction'] ?? '',
                                  style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 9, fontWeight: FontWeight.bold)),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text('${t['entry_price']} → ${t['exit_price']}',
                                      style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
                                    Text(t['reason'] ?? '',
                                      style: const TextStyle(color: Color(0xFF4A4F62), fontFamily: 'monospace', fontSize: 9)),
                                  ],
                                ),
                              ),
                              Text('${win ? "+" : ""}₹${pnl.toStringAsFixed(0)}',
                                style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 13, fontWeight: FontWeight.bold)),
                            ],
                          ),
                        );
                      },
                    ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _stat(String l, String v, Color c) => Container(
    padding: const EdgeInsets.all(10),
    decoration: BoxDecoration(
      color: const Color(0xFF0E1117),
      border: Border.all(color: const Color(0xFF1C2029)),
      borderRadius: BorderRadius.circular(7),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l, style: const TextStyle(color: Color(0xFF4A4F62), fontFamily: 'monospace', fontSize: 8, letterSpacing: 1)),
        Text(v, style: TextStyle(color: c, fontFamily: 'monospace', fontSize: 18, fontWeight: FontWeight.bold)),
      ],
    ),
  );
}
