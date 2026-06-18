import 'package:flutter/material.dart';

// ─── Active trade card ────────────────────────────────────────────────
class TradeCard extends StatelessWidget {
  final Map<String, dynamic>? trade;
  final double currentPrice;
  const TradeCard({super.key, this.trade, required this.currentPrice});

  @override
  Widget build(BuildContext context) {
    if (trade == null) {
      return _panel('ACTIVE TRADE', Container(
        padding: const EdgeInsets.all(20),
        alignment: Alignment.center,
        child: const Text('No active trade',
          style: TextStyle(color: Color(0xFF4A4F62), fontSize: 11)),
      ));
    }
    final dir = trade!['direction'] ?? 'BUY';
    final entry = (trade!['entry_price'] ?? 0).toDouble();
    final qty = trade!['qty_remaining'] ?? trade!['qty_initial'] ?? 0;
    final pnl = (dir == 'BUY' ? currentPrice - entry : entry - currentPrice) * qty;
    final profit = pnl >= 0;
    final color = profit ? const Color(0xFF00D97E) : const Color(0xFFFF4757);
    final partials = List<String>.from(trade!['partials_hit'] ?? []);

    return _panel('ACTIVE TRADE', Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        border: Border.all(color: color.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: (dir == 'BUY' ? const Color(0xFF00D97E) : const Color(0xFFFF4757)).withOpacity(0.2),
                  borderRadius: BorderRadius.circular(3),
                ),
                child: Text(dir, style: TextStyle(
                  color: dir == 'BUY' ? const Color(0xFF00D97E) : const Color(0xFFFF4757),
                  fontFamily: 'monospace', fontSize: 9, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(width: 8),
              Text('$qty @ ${entry.toStringAsFixed(2)}',
                style: const TextStyle(fontFamily: 'monospace', fontSize: 11)),
              const Spacer(),
              Text('${profit ? "+" : ""}₹${pnl.toStringAsFixed(0)}',
                style: TextStyle(color: color, fontFamily: 'monospace', fontSize: 14, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(spacing: 10, children: [
            _meta('SL', trade!['stop_loss']),
            _meta('T1', trade!['target_1']),
            _meta('T2', trade!['target_2']),
            _meta('T3', trade!['target_3']),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            _partial('T1', partials.contains('T1')),
            _partial('T2', partials.contains('T2')),
            _partial('T3', partials.contains('T3')),
          ]),
        ],
      ),
    ));
  }

  Widget _meta(String l, dynamic v) => Text('$l: ${v?.toString() ?? "—"}',
    style: const TextStyle(color: Color(0xFFA0A4B8), fontFamily: 'monospace', fontSize: 9));

  Widget _partial(String l, bool hit) => Container(
    margin: const EdgeInsets.only(right: 5),
    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
    decoration: BoxDecoration(
      color: hit ? const Color(0xFF00D97E).withOpacity(0.2) : const Color(0xFF13161D),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Text('$l ${hit ? "✓" : "—"}',
      style: TextStyle(
        color: hit ? const Color(0xFF00D97E) : const Color(0xFF4A4F62),
        fontFamily: 'monospace', fontSize: 8,
      )),
  );
}

// ─── Reusable panel (local copy) ──────────────────────────────────────
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