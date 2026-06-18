import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/features_state.dart';

class MarketsHubScreen extends StatefulWidget {
  const MarketsHubScreen({super.key});

  @override
  State<MarketsHubScreen> createState() => _MarketsHubScreenState();
}

class _MarketsHubScreenState extends State<MarketsHubScreen> with SingleTickerProviderStateMixin {
  late TabController _tabs;
  final _symbolCtrl = TextEditingController(text: 'RELIANCE');

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 8, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final fs = context.read<FeaturesState>();
      fs.loadDashboard();
      fs.loadWatchlist();
      fs.loadPortfolio();
      fs.loadNews();
      fs.loadOptions();
      fs.loadPaper();
      fs.loadAlerts();
      fs.loadJournal();
    });
  }

  @override
  void dispose() {
    _tabs.dispose();
    _symbolCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(14, 10, 14, 0),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text('MARKETS', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
            ),
          ),
          TabBar(
            controller: _tabs,
            isScrollable: true,
            labelColor: const Color(0xFF00D97E),
            unselectedLabelColor: const Color(0xFF4A4F62),
            indicatorColor: const Color(0xFF00D97E),
            labelStyle: const TextStyle(fontSize: 10, fontFamily: 'monospace'),
            tabs: const [
              Tab(text: 'Live'),
              Tab(text: 'AI Stock'),
              Tab(text: 'Portfolio'),
              Tab(text: 'Watchlist'),
              Tab(text: 'News'),
              Tab(text: 'Technical'),
              Tab(text: 'Paper'),
              Tab(text: 'More'),
            ],
          ),
          Expanded(
            child: Consumer<FeaturesState>(
              builder: (ctx, fs, _) => TabBarView(
                controller: _tabs,
                children: [
                  _LiveTab(fs: fs),
                  _AIStockTab(fs: fs, symbolCtrl: _symbolCtrl),
                  _PortfolioTab(fs: fs, symbolCtrl: _symbolCtrl),
                  _WatchlistTab(fs: fs, symbolCtrl: _symbolCtrl),
                  _NewsTab(fs: fs),
                  _TechnicalTab(fs: fs, symbolCtrl: _symbolCtrl),
                  _PaperTab(fs: fs, symbolCtrl: _symbolCtrl),
                  _MoreTab(fs: fs),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Shared widgets ──
Widget _card(String title, Widget child) => Container(
  margin: const EdgeInsets.only(bottom: 10),
  padding: const EdgeInsets.all(12),
  decoration: BoxDecoration(
    color: const Color(0xFF0E1117),
    border: Border.all(color: const Color(0xFF1C2029)),
    borderRadius: BorderRadius.circular(8),
  ),
  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Text(title, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
    const SizedBox(height: 8),
    child,
  ]),
);

Widget _loading(FeaturesState fs) => fs.loading
    ? const Padding(padding: EdgeInsets.all(20), child: Center(child: CircularProgressIndicator(strokeWidth: 2)))
    : const SizedBox.shrink();

Color _chgColor(num v) => v >= 0 ? const Color(0xFF00D97E) : const Color(0xFFFF4757);

// ── 1. Live Market Dashboard ──
class _LiveTab extends StatelessWidget {
  final FeaturesState fs;
  const _LiveTab({required this.fs});

  @override
  Widget build(BuildContext context) {
    final d = fs.dashboard;
    final indices = List.from(d['indices'] ?? []);
    final movers = d['movers'] ?? {};
    final sectors = List.from(d['sectors'] ?? []);
    final heatmap = List.from(d['heatmap'] ?? []);

    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        if (fs.error != null) Text(fs.error!, style: const TextStyle(color: Color(0xFFFF4757), fontSize: 10)),
        _loading(fs),
        _card('Indices', Column(
          children: indices.map<Widget>((i) => ListTile(
            dense: true,
            title: Text(i['name'] ?? '', style: const TextStyle(fontSize: 11)),
            trailing: Text('${i['ltp']}  ${i['change_pct']}%', style: TextStyle(color: _chgColor(i['change_pct'] ?? 0), fontSize: 10)),
          )).toList(),
        )),
        _card('Top Gainers', _moverList(movers['gainers'])),
        _card('Top Losers', _moverList(movers['losers'])),
        _card('Most Active', _moverList(movers['most_active'])),
        _card('Sector Performance', Column(
          children: sectors.map<Widget>((s) => ListTile(
            dense: true,
            title: Text(s['sector'], style: const TextStyle(fontSize: 10)),
            trailing: Text('${s['change_pct']}%', style: TextStyle(color: _chgColor(s['change_pct'] ?? 0), fontSize: 10)),
          )).toList(),
        )),
        _card('Market Heatmap', Wrap(
          spacing: 4, runSpacing: 4,
          children: heatmap.map<Widget>((h) => Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: (h['direction'] == 'up' ? const Color(0xFF00D97E) : const Color(0xFFFF4757))
                  .withValues(alpha: 0.1 + (h['intensity'] ?? 0.3) * 0.5),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text('${h['symbol']}\n${h['change_pct']}%', style: const TextStyle(fontSize: 8)),
          )).toList(),
        )),
        IconButton(onPressed: fs.loadDashboard, icon: const Icon(Icons.refresh, size: 18)),
      ],
    );
  }

  Widget _moverList(dynamic list) {
    final items = List.from(list ?? []);
    if (items.isEmpty) return const Text('No data — check Fyers token', style: TextStyle(color: Color(0xFF4A4F62), fontSize: 10));
    return Column(children: items.map<Widget>((m) => ListTile(
      dense: true,
      title: Text(m['symbol'], style: const TextStyle(fontSize: 10)),
      subtitle: Text('Vol: ${m['volume']}', style: const TextStyle(fontSize: 8, color: Color(0xFF4A4F62))),
      trailing: Text('${m['change_pct']}%', style: TextStyle(color: _chgColor(m['change_pct'] ?? 0), fontSize: 10)),
    )).toList());
  }
}

// ── 2. AI Stock Analysis ──
class _AIStockTab extends StatelessWidget {
  final FeaturesState fs;
  final TextEditingController symbolCtrl;
  const _AIStockTab({required this.fs, required this.symbolCtrl});

  @override
  Widget build(BuildContext context) {
    final a = fs.aiAnalysis;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Row(children: [
          Expanded(child: TextField(
            controller: symbolCtrl,
            style: const TextStyle(fontSize: 12),
            decoration: const InputDecoration(hintText: 'Symbol e.g. RELIANCE', hintStyle: TextStyle(fontSize: 10)),
          )),
          const SizedBox(width: 8),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00D97E)),
            onPressed: () => fs.analyzeStock(symbolCtrl.text),
            child: const Text('Analyze', style: TextStyle(color: Colors.black, fontSize: 10)),
          ),
        ]),
        _loading(fs),
        if (a.isNotEmpty) ...[
          _card('Sentiment', Text(a['sentiment'] ?? '', style: TextStyle(
            color: a['sentiment'] == 'Bullish' ? const Color(0xFF00D97E) : a['sentiment'] == 'Bearish' ? const Color(0xFFFF4757) : const Color(0xFFF5A623),
            fontSize: 14, fontWeight: FontWeight.bold))),
          _card('Risk Score', Text('${a['risk_score'] ?? '—'} / 10', style: const TextStyle(fontSize: 12))),
          _card('Claude Analysis', Text(a['ai_analysis'] ?? '', style: const TextStyle(fontSize: 10, height: 1.4))),
        ],
      ],
    );
  }
}

// ── 3. Portfolio ──
class _PortfolioTab extends StatelessWidget {
  final FeaturesState fs;
  final TextEditingController symbolCtrl;
  const _PortfolioTab({required this.fs, required this.symbolCtrl});

  @override
  Widget build(BuildContext context) {
    final p = fs.portfolio;
    final s = p['summary'] ?? {};
    final advisor = fs.portfolioAdvisor;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        _card('Summary', Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Value: ₹${s['total_value'] ?? 0}', style: const TextStyle(fontSize: 12)),
          Text('P&L: ₹${s['total_pnl'] ?? 0} (${s['total_pnl_pct'] ?? 0}%)', style: TextStyle(color: _chgColor(s['total_pnl'] ?? 0), fontSize: 11)),
          Text('Health: ${advisor['health_score'] ?? '—'}/100', style: const TextStyle(fontSize: 10, color: Color(0xFF4A4F62))),
        ])),
        _card('Holdings', Column(
          children: (p['holdings'] as List? ?? []).map<Widget>((h) => ListTile(
            dense: true,
            title: Text('${h['symbol']} x${h['qty']}', style: const TextStyle(fontSize: 10)),
            subtitle: Text('Avg ₹${h['avg_price']} → ₹${h['ltp']}', style: const TextStyle(fontSize: 9)),
            trailing: Text('${h['pnl_pct']}%', style: TextStyle(color: _chgColor(h['pnl_pct'] ?? 0), fontSize: 10)),
          )).toList(),
        )),
        _card('AI Advisor', Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: (advisor['rebalance_suggestions'] as List? ?? ['Add holdings to get advice'])
              .map<Widget>((s) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text('• $s', style: const TextStyle(fontSize: 9, color: Color(0xFFA0A4B8))),
              )).toList(),
        )),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00D97E)),
          onPressed: () => fs.addHolding(symbolCtrl.text, 10, 1000),
          child: Text('Add ${symbolCtrl.text} (demo)', style: const TextStyle(color: Colors.black, fontSize: 10)),
        ),
      ],
    );
  }
}

// ── 5. Watchlist ──
class _WatchlistTab extends StatelessWidget {
  final FeaturesState fs;
  final TextEditingController symbolCtrl;
  const _WatchlistTab({required this.fs, required this.symbolCtrl});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Row(children: [
          Expanded(child: TextField(controller: symbolCtrl, style: const TextStyle(fontSize: 12))),
          IconButton(onPressed: () => fs.addWatchlist(symbolCtrl.text), icon: const Icon(Icons.add, color: Color(0xFF00D97E))),
        ]),
        ...fs.watchlist.map<Widget>((w) {
          final sc = w['scores'] ?? {};
          return _card(w['symbol'], Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('₹${w['price']}  |  ${sc['signal'] ?? ''}', style: const TextStyle(fontSize: 11)),
            const SizedBox(height: 6),
            Row(children: [
              _scoreChip('BUY', sc['buy'], const Color(0xFF00D97E)),
              _scoreChip('HOLD', sc['hold'], const Color(0xFFF5A623)),
              _scoreChip('SELL', sc['sell'], const Color(0xFFFF4757)),
            ]),
            Text('RSI ${sc['rsi']} | ${sc['trend']}', style: const TextStyle(fontSize: 9, color: Color(0xFF4A4F62))),
          ]));
        }),
      ],
    );
  }

  Widget _scoreChip(String label, dynamic v, Color c) => Expanded(
    child: Container(
      margin: const EdgeInsets.only(right: 4),
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
      child: Text('$label\n$v%', textAlign: TextAlign.center, style: TextStyle(fontSize: 8, color: c)),
    ),
  );
}

// ── 6. News ──
class _NewsTab extends StatelessWidget {
  final FeaturesState fs;
  const _NewsTab({required this.fs});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(12),
      children: fs.news.map<Widget>((n) => _card(n['title'] ?? '', Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(n['sentiment_label'] ?? '', style: TextStyle(
            fontSize: 9,
            color: n['sentiment_label'] == 'Positive' ? const Color(0xFF00D97E) : n['sentiment_label'] == 'Negative' ? const Color(0xFFFF4757) : const Color(0xFFF5A623),
          )),
          const SizedBox(height: 4),
          Text(n['source'] ?? '', style: const TextStyle(fontSize: 8, color: Color(0xFF4A4F62))),
        ],
      ))).toList(),
    );
  }
}

// ── 7. Technical ──
class _TechnicalTab extends StatelessWidget {
  final FeaturesState fs;
  final TextEditingController symbolCtrl;
  const _TechnicalTab({required this.fs, required this.symbolCtrl});

  @override
  Widget build(BuildContext context) {
    final t = fs.technical;
    final ind = t['indicators'] ?? {};
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Row(children: [
          Expanded(child: TextField(controller: symbolCtrl, style: const TextStyle(fontSize: 12))),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00D97E)),
            onPressed: () => fs.loadTechnical(symbolCtrl.text),
            child: const Text('Load', style: TextStyle(color: Colors.black, fontSize: 10)),
          ),
        ]),
        if (t.isNotEmpty) ...[
          _card('Indicators', Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _ind('RSI', ind['rsi']), _ind('MACD', ind['macd']), _ind('EMA20', ind['ema20']),
            _ind('SMA20', ind['sma20']), _ind('VWAP', ind['vwap']), _ind('ATR', ind['atr']),
            _ind('ADX', ind['adx']), _ind('BB Upper', ind['bb_upper']), _ind('BB Lower', ind['bb_lower']),
          ])),
          _card('Support / Resistance', Text(
            'Support: ${t['support_resistance']?['support']}  |  Resistance: ${t['support_resistance']?['resistance']}',
            style: const TextStyle(fontSize: 10))),
          _card('Pattern', Text('${t['pattern'] ?? 'None'}', style: const TextStyle(fontSize: 10))),
          _card('Fibonacci', Text('${t['fibonacci']}', style: const TextStyle(fontSize: 9))),
        ],
      ],
    );
  }

  Widget _ind(String k, dynamic v) => Padding(
    padding: const EdgeInsets.only(bottom: 3),
    child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
      Text(k, style: const TextStyle(fontSize: 10, color: Color(0xFF4A4F62))),
      Text('$v', style: const TextStyle(fontSize: 10)),
    ]),
  );
}

// ── 10. Paper Trading ──
class _PaperTab extends StatelessWidget {
  final FeaturesState fs;
  final TextEditingController symbolCtrl;
  const _PaperTab({required this.fs, required this.symbolCtrl});

  @override
  Widget build(BuildContext context) {
    final a = fs.paperAccount;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        _card('Virtual Account', Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Cash: ₹${a['cash'] ?? 0}', style: const TextStyle(fontSize: 12)),
          Text('Equity: ₹${a['total_equity'] ?? 0}', style: const TextStyle(fontSize: 11)),
          Text('Realized P&L: ₹${a['realized_pnl'] ?? 0}', style: TextStyle(color: _chgColor(a['realized_pnl'] ?? 0), fontSize: 11)),
          Text('Win rate: ${a['win_rate'] ?? 0}%', style: const TextStyle(fontSize: 10, color: Color(0xFF4A4F62))),
        ])),
        Row(children: [
          Expanded(child: TextField(controller: symbolCtrl, style: const TextStyle(fontSize: 12))),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00D97E)),
            onPressed: () => fs.paperBuy(symbolCtrl.text, 1),
            child: const Text('BUY', style: TextStyle(color: Colors.black, fontSize: 10)),
          ),
        ]),
        _card('Recent Trades', Column(
          children: fs.paperTrades.take(10).map<Widget>((t) => ListTile(
            dense: true,
            title: Text('${t['direction']} ${t['symbol']}', style: const TextStyle(fontSize: 10)),
            trailing: Text('₹${t['pnl'] ?? 0}', style: TextStyle(color: _chgColor(t['pnl'] ?? 0), fontSize: 10)),
          )).toList(),
        )),
      ],
    );
  }
}

// ── Options, Screener, Alerts, Journal ──
class _MoreTab extends StatelessWidget {
  final FeaturesState fs;
  const _MoreTab({required this.fs});

  @override
  Widget build(BuildContext context) {
    final o = fs.options;
    final ja = fs.journalAi;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        _card('Options Dashboard', Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('PCR: ${o['pcr']} (${o['pcr_signal']})', style: const TextStyle(fontSize: 10)),
          Text('Max Pain: ${o['max_pain']}', style: const TextStyle(fontSize: 10)),
          Text('VIX: ${o['vix']} — ${o['vix_regime']}', style: const TextStyle(fontSize: 10)),
          Text('${o['oi_signal']}', style: const TextStyle(fontSize: 9, color: Color(0xFF4A4F62))),
        ])),
        _card('AI Screener', Column(children: [
          Wrap(spacing: 6, children: [
            _presetBtn(context, 'oversold', 'Oversold'),
            _presetBtn(context, 'breakout', 'Breakout'),
            _presetBtn(context, 'uptrend', 'Uptrend'),
          ]),
          const SizedBox(height: 8),
          ...fs.screenerResults.take(8).map<Widget>((s) => ListTile(
            dense: true,
            title: Text(s['symbol'], style: const TextStyle(fontSize: 10)),
            subtitle: Text('RSI ${s['rsi']} | ${s['change_signal']}', style: const TextStyle(fontSize: 8)),
          )),
        ])),
        _card('Smart Alerts', Text('${fs.alerts.length} active alerts', style: const TextStyle(fontSize: 10))),
        _card('AI Trade Journal', Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Win rate: ${ja['summary']?['win_rate'] ?? '—'}%', style: const TextStyle(fontSize: 10)),
          const SizedBox(height: 6),
          Text(ja['ai_insights'] ?? '', style: const TextStyle(fontSize: 9, height: 1.4, color: Color(0xFFA0A4B8))),
        ])),
        IconButton(onPressed: () { fs.loadOptions(); fs.loadJournal(); }, icon: const Icon(Icons.refresh, size: 18)),
      ],
    );
  }

  Widget _presetBtn(BuildContext ctx, String preset, String label) => ActionChip(
    label: Text(label, style: const TextStyle(fontSize: 9)),
    onPressed: () => fs.runScreener(preset),
  );
}
