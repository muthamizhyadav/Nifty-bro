import 'package:flutter/material.dart';
import 'package:nifty_ai_bot/widgets/signal_card.dart';
import 'package:provider/provider.dart';
import '../state/bot_state.dart';
import '../widgets/candlestick_chart.dart';
import '../widgets/trade_card.dart';
import '../widgets/stats_row.dart' as stats_row;
import '../widgets/log_panel.dart' as log_panel;


class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Consumer<BotState>(
        builder: (ctx, state, _) => Column(
          children: [
            PriceHeader(state: state),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(10),
                children: [
                  // Timeframe selector
                  _TimeframeSelector(state: state),
                  const SizedBox(height: 8),

                  // Candlestick chart with trade overlays
                  Container(
                    height: 520,
                    decoration: BoxDecoration(
                      color: const Color(0xFF0E1117),
                      border: Border.all(color: const Color(0xFF1C2029)),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: CandlestickChart(
                      candles: state.candles,
                      liveCandle: state.liveCandle,
                      activeTrade: state.activeTrade,
                      activeSignal: state.activeSignal,
                      currentPrice: state.currentPrice,
                    ),
                  ),
                  const SizedBox(height: 10),

                  // Signal card
                  SignalCard(
                    signal: state.activeSignal,
                    statusMessage: state.statusMessage,
                    marketDataOk: state.marketDataOk,
                  ),
                  const SizedBox(height: 10),

                  // Active trade card
                  TradeCard(trade: state.activeTrade, currentPrice: state.currentPrice),
                  const SizedBox(height: 10),

                  // Stats
                  stats_row.StatsRow(stats: state.stats),
                  const SizedBox(height: 10),

                  // Activity log
                  log_panel.LogPanel(logs: state.logs),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TimeframeSelector extends StatelessWidget {
  final BotState state;
  const _TimeframeSelector({required this.state});

  @override
  Widget build(BuildContext context) {
    const timeframes = ['5m', '15m', '1h', '3h'];
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFF0E1117),
        border: Border.all(color: const Color(0xFF1C2029)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: timeframes.map((tf) {
          final selected = state.selectedTimeframe == tf;
          return Expanded(
            child: GestureDetector(
              onTap: () => state.setTimeframe(tf),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 2),
                padding: const EdgeInsets.symmetric(vertical: 8),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: selected ? const Color(0xFF00D97E) : Colors.transparent,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  tf,
                  style: TextStyle(
                    color: selected ? Colors.black : const Color(0xFF8A8E9C),
                    fontWeight: selected ? FontWeight.bold : FontWeight.normal,
                    fontSize: 12,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}