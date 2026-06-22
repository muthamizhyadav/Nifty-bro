import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import '../state/bot_state.dart';
import '../utils/market_time.dart';

/// TradingView-style candlestick chart.
/// - Dynamic Y axis with round price levels
/// - Adaptive X axis (HH:MM for intraday, DD/MM for daily)
/// - Crosshair on hover with OHLCV tooltip
/// - Volume bars (transparent, bottom)
/// - Drag to pan, scroll to zoom, +/- buttons
/// - Bot prediction overlays (entry/SL/targets)
class CandlestickChart extends StatefulWidget {
  final List<Candle> candles;
  final Candle? liveCandle;
  final Map<String, dynamic>? activeTrade;
  final Map<String, dynamic>? activeSignal;
  final double currentPrice;
  final bool marketOpen;

  const CandlestickChart({
    super.key,
    required this.candles,
    this.liveCandle,
    this.activeTrade,
    this.activeSignal,
    required this.currentPrice,
    this.marketOpen = false,
  });

  @override
  State<CandlestickChart> createState() => _CandlestickChartState();
}

class _CandlestickChartState extends State<CandlestickChart> {
  int _visibleCount = 60;
  double _offset = 0;
  double _chartWidth = 400;
  Offset? _mouse;

  Candle? get _formingCandle {
    if (widget.liveCandle != null) return widget.liveCandle;
    if (!widget.marketOpen || widget.currentPrice <= 0 || widget.candles.isEmpty) {
      return null;
    }
    final last = widget.candles.last;
    return Candle(
      time: last.time,
      open: last.open,
      high: last.high > widget.currentPrice ? last.high : widget.currentPrice,
      low: last.low < widget.currentPrice ? last.low : widget.currentPrice,
      close: widget.currentPrice,
      volume: last.volume,
    );
  }

  List<Candle> get _all {
    final list = <Candle>[...widget.candles];
    final live = _formingCandle;
    if (live == null) return list;
    // Replace forming bar instead of duplicating last historical candle
    if (list.isNotEmpty &&
        MarketTime.sameCandleBucket(list.last.time, live.time)) {
      list[list.length - 1] = live;
    } else if (widget.marketOpen) {
      list.add(live);
    }
    return list;
  }

  void _zoom(int delta) {
    setState(() => _visibleCount = (_visibleCount + delta).clamp(15, 300));
  }

  @override
  Widget build(BuildContext context) {
    final all = _all;
    if (all.length < 2) {
      return const Center(
        child: Text('Loading candles...\nReconnect Fyers if this persists.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Color(0xFF4A4F62), fontSize: 11)),
      );
    }
    final maxOff = (all.length - _visibleCount).clamp(0, all.length).toDouble();

    return Stack(children: [
      LayoutBuilder(builder: (ctx, box) {
        _chartWidth = box.maxWidth;
        return Listener(
          onPointerSignal: (event) {
            if (event is PointerScrollEvent) {
              setState(() {
                _visibleCount = (_visibleCount + (event.scrollDelta.dy > 0 ? 5 : -5)).clamp(15, 300);
              });
            }
          },
          child: MouseRegion(
            onHover: (e) => setState(() => _mouse = e.localPosition),
            onExit: (_) => setState(() => _mouse = null),
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onHorizontalDragUpdate: (d) {
                setState(() {
                  final cw = _chartWidth / _visibleCount;
                  _offset = (_offset - d.delta.dx / cw).clamp(0.0, maxOff);
                });
              },
              child: CustomPaint(
                painter: _TVPainter(
                  candles: all,
                  visibleCount: _visibleCount,
                  offset: _offset.clamp(0.0, maxOff),
                  activeTrade: widget.activeTrade,
                  activeSignal: widget.activeSignal,
                  currentPrice: widget.currentPrice,
                  mouse: _mouse,
                ),
                child: const SizedBox.expand(),
              ),
            ),
          ),
        );
      }),
      Positioned(top: 6, left: 6, child: Row(children: [
        _btn(Icons.remove, () => _zoom(15)),
        const SizedBox(width: 4),
        _btn(Icons.add, () => _zoom(-15)),
      ])),
    ]);
  }

  Widget _btn(IconData icon, VoidCallback onTap) => GestureDetector(
    onTap: onTap,
    child: Container(
      width: 26, height: 26,
      decoration: BoxDecoration(
        color: const Color(0xFF1C2029), borderRadius: BorderRadius.circular(4),
        border: Border.all(color: const Color(0xFF2D3142))),
      child: Icon(icon, size: 14, color: const Color(0xFF8A8E9C)),
    ),
  );
}

// ===================================================================
// TradingView-style painter
// ===================================================================
class _TVPainter extends CustomPainter {
  final List<Candle> candles;
  final int visibleCount;
  final double offset;
  final Map<String, dynamic>? activeTrade;
  final Map<String, dynamic>? activeSignal;
  final double currentPrice;
  final Offset? mouse;

  _TVPainter({
    required this.candles, required this.visibleCount, required this.offset,
    this.activeTrade, this.activeSignal, required this.currentPrice, this.mouse,
  });

  static const padL = 4.0, padR = 62.0, padT = 6.0, padB = 22.0;
  static const volFrac = 0.15;

  double? _num(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString().split('-').first.trim());
  }

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    canvas.drawRect(Offset.zero & size, Paint()..color = const Color(0xFF0C0E14));

    final total = candles.length;
    final count = visibleCount.clamp(2, total);
    final endIdx = (total - offset).round().clamp(count, total);
    final startIdx = (endIdx - count).clamp(0, total - 1);
    final visible = candles.sublist(startIdx, endIdx);
    if (visible.length < 2) return;

    // Price range
    double mn = double.infinity, mx = -double.infinity;
    double maxVol = 0;
    for (final c in visible) {
      if (c.low < mn) mn = c.low;
      if (c.high > mx) mx = c.high;
      final v = c.volume > 0 ? c.volume.toDouble() : (c.high - c.low).abs() * 1000 + 1;
      if (v > maxVol) maxVol = v;
    }
    final pad = (mx - mn) * 0.05 + 0.5;
    mn -= pad; mx += pad;
    final range = (mx - mn).clamp(0.01, double.infinity);

    final chartH = h - padT - padB;
    final priceH = chartH * (1 - volFrac);
    final volH = chartH * volFrac;
    final chartW = w - padL - padR;
    final cw = chartW / count;

    double toY(double p) => padT + (mx - p) / range * priceH;
    double volY(double v) => padT + priceH + volH - (v / maxVol.clamp(1, double.infinity)) * volH;

    final tp = TextPainter(textDirection: TextDirection.ltr);

    // -- Y AXIS: dynamic round price levels --
    final step = _niceStep(range, 8);
    final firstLevel = (mn / step).ceil() * step;
    final yAxisPaint = Paint()..color = const Color(0xFF1A1D24)..strokeWidth = 0.5;
    for (double p = firstLevel; p <= mx; p += step) {
      final y = toY(p);
      if (y < padT || y > padT + priceH) continue;
      canvas.drawLine(Offset(padL, y), Offset(w - padR, y), yAxisPaint);
      tp.text = TextSpan(text: p.toStringAsFixed(p >= 1000 ? 0 : 1),
        style: const TextStyle(color: Color(0xFF5C6070), fontSize: 10, fontFamily: 'monospace'));
      tp.layout();
      tp.paint(canvas, Offset(w - padR + 6, y - tp.height / 2));
    }

    // Volume separator
    canvas.drawLine(Offset(padL, padT + priceH), Offset(w - padR, padT + priceH),
      Paint()..color = const Color(0xFF1A1D24)..strokeWidth = 0.5);

    // -- X AXIS: adaptive time labels --
    final labelEvery = (count / 6).clamp(1, count).round();
    for (int i = 0; i < visible.length; i += labelEvery) {
      final c = visible[i];
      final dt = MarketTime.istFromEpoch(c.time);
      final x = padL + i * cw + cw / 2;
      String label;
      if (visible.length > 1) {
        final t0 = MarketTime.epochSeconds(visible[0].time);
        final t1 = MarketTime.epochSeconds(visible[1].time);
        final gap = (t1 - t0).abs();
        if (gap < 3600) {
          label = '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
        } else if (gap < 86400) {
          label = '${dt.day}/${dt.month} ${dt.hour}:00';
        } else {
          label = '${dt.day} ${_monthName(dt.month)}';
        }
      } else {
        label = '${dt.day}/${dt.month}';
      }
      tp.text = TextSpan(text: label,
        style: const TextStyle(color: Color(0xFF5C6070), fontSize: 9, fontFamily: 'monospace'));
      tp.layout();
      if (x - tp.width / 2 > padL && x + tp.width / 2 < w - padR) {
        tp.paint(canvas, Offset(x - tp.width / 2, h - padB + 4));
      }
    }

    // -- Volume bars --
    final volPaint = Paint()..isAntiAlias = true;
    for (int i = 0; i < visible.length; i++) {
      final c = visible[i];
      final bull = c.close >= c.open;
      final vol = c.volume > 0 ? c.volume.toDouble() : (c.high - c.low).abs() * 1000 + 1;
      volPaint.color = (bull ? const Color(0xFF26A69A) : const Color(0xFFEF5350)).withOpacity(0.25);
      final cx = padL + i * cw + cw / 2;
      final bw = (cw * 0.7).clamp(1.0, 14.0);
      final top = volY(vol);
      final bot = padT + priceH + volH;
      canvas.drawRect(Rect.fromLTRB(cx - bw / 2, top, cx + bw / 2, bot), volPaint);
    }

    // -- Candles --
    final wickP = Paint()..isAntiAlias = true;
    final bodyP = Paint()..isAntiAlias = true..style = PaintingStyle.fill;
    for (int i = 0; i < visible.length; i++) {
      final c = visible[i];
      final cx = padL + i * cw + cw / 2;
      final bull = c.close >= c.open;
      final color = bull ? const Color(0xFF26A69A) : const Color(0xFFEF5350);

      wickP.color = color;
      wickP.strokeWidth = (cw * 0.08).clamp(0.5, 1.5);
      canvas.drawLine(Offset(cx, toY(c.high)), Offset(cx, toY(c.low)), wickP);

      final yO = toY(c.open), yC = toY(c.close);
      double top = min(yO, yC), bot = max(yO, yC);
      if (bot - top < 1.0) { top -= 0.5; bot += 0.5; }
      final bw = (cw * 0.7).clamp(1.5, 14.0);
      bodyP.color = color;
      canvas.drawRect(Rect.fromLTRB(cx - bw / 2, top, cx + bw / 2, bot), bodyP);
    }

    // -- Prediction overlays --
    final levels = _overlayLevels();
    _drawLvl(canvas, w, toY, levels['entry'], const Color(0xFF2196F3), 'Entry', solid: true);
    _drawLvl(canvas, w, toY, levels['sl'], const Color(0xFFEF5350), 'SL');
    _drawLvl(canvas, w, toY, levels['t1'], const Color(0xFF26A69A), 'T1');
    _drawLvl(canvas, w, toY, levels['t2'], const Color(0xFF26A69A), 'T2');
    _drawLvl(canvas, w, toY, levels['t3'], const Color(0xFF26A69A), 'T3');

    // -- Current price line + tag --
    if (currentPrice > 0 && currentPrice >= mn && currentPrice <= mx) {
      final y = toY(currentPrice);
      _dash(canvas, Offset(padL, y), Offset(w - padR, y),
        Paint()..color = const Color(0xFF2196F3)..strokeWidth = 0.7);
      final tagW = padR - 4;
      final tagRect = Rect.fromLTWH(w - padR + 2, y - 10, tagW, 20);
      canvas.drawRRect(RRect.fromRectAndRadius(tagRect, const Radius.circular(3)),
        Paint()..color = const Color(0xFF2196F3));
      tp.text = TextSpan(text: currentPrice.toStringAsFixed(1),
        style: const TextStyle(color: Colors.white, fontSize: 10,
          fontWeight: FontWeight.bold, fontFamily: 'monospace'));
      tp.layout();
      tp.paint(canvas, Offset(w - padR + 4, y - tp.height / 2));
    }

    // -- Signal badge --
    final sig = activeSignal?['signal'] ??
      (activeTrade?['direction'] == 'BUY' ? 'LONG' : activeTrade?['direction'] == 'SELL' ? 'SHORT' : null);
    if (sig != null && sig != 'WAIT') {
      final bc = (sig == 'LONG' || sig == 'BUY') ? const Color(0xFF26A69A) : const Color(0xFFEF5350);
      final conf = activeSignal?['confidence'];
      final label = conf != null ? ' $sig $conf% ' : ' $sig ';
      tp.text = TextSpan(text: label,
        style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold, fontFamily: 'monospace'));
      tp.layout();
      final bgRect = RRect.fromRectAndRadius(
        Rect.fromLTWH(padL + 40, padT + 4, tp.width + 6, 20), const Radius.circular(4));
      canvas.drawRRect(bgRect, Paint()..color = bc);
      tp.paint(canvas, Offset(padL + 43, padT + 7));
    }

    // -- CROSSHAIR (TradingView hover) --
    if (mouse != null && mouse!.dx > padL && mouse!.dx < w - padR &&
        mouse!.dy > padT && mouse!.dy < padT + priceH) {
      final crossP = Paint()..color = const Color(0xFF555E6E)..strokeWidth = 0.5;
      canvas.drawLine(Offset(mouse!.dx, padT), Offset(mouse!.dx, padT + priceH + volH), crossP);
      canvas.drawLine(Offset(padL, mouse!.dy), Offset(w - padR, mouse!.dy), crossP);

      // Price at mouse Y
      final mousePrice = mx - (mouse!.dy - padT) / priceH * range;
      tp.text = TextSpan(text: mousePrice.toStringAsFixed(1),
        style: const TextStyle(color: Colors.white, fontSize: 9, fontFamily: 'monospace'));
      tp.layout();
      canvas.drawRect(Rect.fromLTWH(w - padR + 1, mouse!.dy - 8, padR - 2, 16),
        Paint()..color = const Color(0xFF363A45));
      tp.paint(canvas, Offset(w - padR + 4, mouse!.dy - 5));

      // Hovered candle OHLC tooltip
      final candleIdx = ((mouse!.dx - padL) / cw).floor().clamp(0, visible.length - 1);
      final hc = visible[candleIdx];
      final dt = MarketTime.istFromEpoch(hc.time);
      final bull = hc.close >= hc.open;
      final ohlcColor = bull ? const Color(0xFF26A69A) : const Color(0xFFEF5350);
      final info = 'O ${hc.open.toStringAsFixed(1)}  H ${hc.high.toStringAsFixed(1)}  '
                    'L ${hc.low.toStringAsFixed(1)}  C ${hc.close.toStringAsFixed(1)}  '
                    '${dt.day}/${dt.month} ${dt.hour.toString().padLeft(2,"0")}:${dt.minute.toString().padLeft(2,"0")}';
      tp.text = TextSpan(text: info,
        style: TextStyle(color: ohlcColor, fontSize: 10, fontFamily: 'monospace'));
      tp.layout();
      final ohlcY = padT + (sig != null && sig != 'WAIT' ? 28.0 : 4.0);
      canvas.drawRect(Rect.fromLTWH(padL + 40, ohlcY, tp.width + 8, 16),
        Paint()..color = const Color(0xFF0C0E14));
      tp.paint(canvas, Offset(padL + 44, ohlcY + 2));

      // Time label at mouse X
      final timeLabel = '${dt.day}/${dt.month} ${dt.hour.toString().padLeft(2,"0")}:${dt.minute.toString().padLeft(2,"0")}';
      tp.text = TextSpan(text: timeLabel,
        style: const TextStyle(color: Colors.white, fontSize: 9, fontFamily: 'monospace'));
      tp.layout();
      canvas.drawRect(Rect.fromLTWH(mouse!.dx - tp.width / 2 - 3, h - padB - 2, tp.width + 6, 16),
        Paint()..color = const Color(0xFF363A45));
      tp.paint(canvas, Offset(mouse!.dx - tp.width / 2, h - padB));
    }
  }

  // Dynamic Y axis step - gives round numbers like TradingView
  // Zoomed in: 5, 10, 20, 25 point steps
  // Zoomed out: 50, 100, 200, 250, 500 point steps
  double _niceStep(double range, int target) {
    final raw = range / target;
    final mag = pow(10, (log(raw) / ln10).floor()).toDouble();
    final res = raw / mag;
    double nice;
    if (res <= 1.0) { nice = 1.0; }
    else if (res <= 2.0) { nice = 2.0; }
    else if (res <= 2.5) { nice = 2.5; }
    else if (res <= 5.0) { nice = 5.0; }
    else { nice = 10.0; }
    return nice * mag;
  }

  String _monthName(int m) =>
    const ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m];

  Map<String, double?> _overlayLevels() {
    final src = activeTrade ?? activeSignal;
    if (src == null) return {};
    return {
      'entry': _num(src['entry_price'] ?? src['entry_zone']),
      'sl': _num(src['stop_loss']),
      't1': _num(src['target_1']),
      't2': _num(src['target_2']),
      't3': _num(src['target_3']),
    };
  }

  void _drawLvl(Canvas canvas, double w, double Function(double) toY,
      double? price, Color color, String label, {bool solid = false}) {
    if (price == null || price <= 0) return;
    final y = toY(price);
    final p = Paint()..color = solid ? color : color.withOpacity(0.6)
      ..strokeWidth = 1.0..isAntiAlias = true;
    if (solid) {
      canvas.drawLine(Offset(padL, y), Offset(w - padR, y), p);
    } else {
      _dash(canvas, Offset(padL, y), Offset(w - padR, y), p);
    }
    final tp = TextPainter(
      text: TextSpan(text: '$label ${price.toStringAsFixed(0)}',
        style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
      textDirection: TextDirection.ltr)..layout();
    canvas.drawRect(Rect.fromLTWH(padL + 2, y - 12, tp.width + 6, 13),
      Paint()..color = const Color(0xFF0C0E14));
    tp.paint(canvas, Offset(padL + 5, y - 11));
  }

  void _dash(Canvas c, Offset a, Offset b, Paint p) {
    final d = (b - a).distance;
    if (d <= 0) return;
    final dir = (b - a) / d;
    double i = 0;
    while (i < d) {
      c.drawLine(a + dir * i, a + dir * min(i + 4, d), p);
      i += 7;
    }
  }

  @override
  bool shouldRepaint(_TVPainter old) => true;
}