import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:url_launcher/url_launcher.dart';
import '../config/api_config.dart';

String get API_URL => apiBaseUrl;
String get WS_URL => wsBaseUrl;

class Candle {
  final int time;
  final double open, high, low, close;
  final int volume;
  Candle({required this.time, required this.open, required this.high,
          required this.low, required this.close, required this.volume});

  factory Candle.fromJson(Map<String, dynamic> j) => Candle(
    time: j['time'] ?? 0,
    open: (j['open'] ?? 0).toDouble(),
    high: (j['high'] ?? 0).toDouble(),
    low: (j['low'] ?? 0).toDouble(),
    close: (j['close'] ?? 0).toDouble(),
    volume: j['volume'] ?? 0,
  );
}

class BotState extends ChangeNotifier {
  WebSocketChannel? _ws;
  bool running = false;
  bool connected = false;       // WebSocket live
  bool backendReachable = false; // REST API reachable
  bool authenticated = false;
  bool marketDataOk = false;
  String? statusMessage;

  double currentPrice = 0;
  String selectedTimeframe = '15m';  // 5m, 15m, 1h, 3h
  Candle? liveCandle;  // the currently-forming candle
  List<Candle> candles = [];
  Map<String, dynamic>? activeSignal;
  Map<String, dynamic>? activeTrade;
  List<Map<String, dynamic>> trades = [];
  Map<String, dynamic> stats = {};
  List<Map<String, String>> logs = [];

  void connect() {
    _ws?.sink.close();
    connected = false;
    notifyListeners();
    try {
      _addLog('Connecting to $WS_URL ...', 'blue');
      _ws = WebSocketChannel.connect(Uri.parse(WS_URL));
      _ws!.stream.listen(
        _handleMessage,
        onError: (e) {
          connected = false;
          _addLog('WebSocket error: $e', 'red');
          notifyListeners();
          _reconnect();
        },
        onDone: () {
          connected = false;
          _addLog('WebSocket disconnected', 'amber');
          notifyListeners();
          _reconnect();
        },
      );
      fetchInitial();
      fetchCandles();
    } catch (e) {
      connected = false;
      _addLog('Connection failed: $e', 'red');
      _reconnect();
    }
    notifyListeners();
  }

  void _reconnect() {
    Future.delayed(const Duration(seconds: 5), connect);
  }

  void _handleMessage(dynamic raw) {
    try {
      final msg = jsonDecode(raw as String);
      final type = msg['type'];
      final data = msg['data'];

      switch (type) {
        case 'tick':
          currentPrice = (data['price'] ?? 0).toDouble();
          // Backend's forming candle is 15m — only overlay it on the 15m view
          if (data['live_candle'] != null && selectedTimeframe == '15m') {
            liveCandle = Candle.fromJson(data['live_candle']);
          }
          break;
        case 'candle_close':
          // Backend closes 15m candles. Only auto-append on the 15m view;
          // other timeframes refresh via fetchCandles().
          if (selectedTimeframe == '15m') {
            final c = Candle.fromJson(data['candle']);
            candles.add(c);
            if (candles.length > 100) candles.removeAt(0);
            liveCandle = null;
          }
          _addLog('15m candle closed', 'blue');
          break;
        case 'signal':
          activeSignal = data;
          _addLog('Signal: ${data['signal']} (${data['confidence']}%)',
                  data['signal'] == 'LONG' ? 'green' : data['signal'] == 'SHORT' ? 'red' : 'amber');
          break;
        case 'trade_opened':
          activeTrade = data;
          _addLog('Trade opened: ${data['direction']} @ ${data['entry_price']}', 'green');
          break;
        case 'partial_exit':
          _addLog('${data['label']} hit @ ${data['price']} | PnL: ₹${data['pnl']}', 'green');
          break;
        case 'trade_closed':
          activeTrade = null;
          _addLog('Trade closed: ${data['exit_reason']} | PnL: ₹${data['final_pnl']}',
                  (data['final_pnl'] ?? 0) > 0 ? 'green' : 'red');
          fetchInitial();
      fetchCandles();
          break;
        case 'bot_started':
          running = true; _addLog('Bot started', 'green');
          break;
        case 'bot_stopped':
          running = false; _addLog('Bot stopped', 'amber');
          break;
        case 'history_loaded':
          if (data['candles'] != null) {
            candles = (data['candles'] as List).map((c) => Candle.fromJson(c)).toList();
            _addLog('Loaded ${candles.length} historical candles', 'blue');
          }
          break;
        case 'init':
          connected = true;
          if (data['candles'] != null) {
            candles = (data['candles'] as List).map((c) => Candle.fromJson(c)).toList();
          }
          stats = Map<String, dynamic>.from(data['stats'] ?? {});
          activeTrade = data['active_trade'];
          running = data['running'] ?? false;
          authenticated = data['authenticated'] ?? false;
          _addLog('WebSocket connected', 'green');
          break;
        case 'mcp_reply':
          // Handled by McpState via separate listener if needed
          break;
      }
      notifyListeners();
    } catch (e) {
      _addLog('Parse error: $e', 'red');
    }
  }

  void _addLog(String msg, String color) {
    final t = DateTime.now().toString().substring(11, 19);
    logs.insert(0, {'time': t, 'msg': msg, 'color': color});
    if (logs.length > 50) logs.removeLast();
  }

  Future<void> fetchInitial() async {
    try {
      final res = await Future.wait([
        http.get(Uri.parse('$API_URL/status')),
        http.get(Uri.parse('$API_URL/stats')),
        http.get(Uri.parse('$API_URL/trades?limit=50')),
      ]);
      final status = jsonDecode(res[0].body);
      backendReachable = true;
      running = status['running'] ?? false;
      activeTrade = status['active_trade'];
      authenticated = status['authenticated'] ?? authenticated;
      marketDataOk = status['market_data_ok'] ?? false;
      statusMessage = status['message'];
      if ((status['current_price'] ?? 0) > 0) {
        currentPrice = (status['current_price']).toDouble();
      }
      stats = Map<String, dynamic>.from(jsonDecode(res[1].body));
      trades = List<Map<String, dynamic>>.from(jsonDecode(res[2].body));
      notifyListeners();
    } catch (e) {
      backendReachable = false;
      _addLog('Backend unreachable: $e', 'red');
      notifyListeners();
    }
  }

  Future<void> toggleBot() async {
    final endpoint = running ? '/bot/stop' : '/bot/start';
    try {
      await http.post(Uri.parse('$API_URL$endpoint'));
    } catch (e) {
      _addLog('Toggle error: $e', 'red');
    }
  }

  Future<void> setTimeframe(String tf) async {
    selectedTimeframe = tf;
    liveCandle = null;  // clear forming candle when switching
    notifyListeners();
    await fetchCandles();
  }

  Future<void> fetchCandles() async {
    try {
      final res = await http.get(
        Uri.parse('$API_URL/candles?tf=$selectedTimeframe&limit=1000'));
      final list = jsonDecode(res.body) as List;
      candles = list.map((c) => Candle.fromJson(c)).toList();
      _addLog('Loaded ${candles.length} $selectedTimeframe candles', 'blue');
      notifyListeners();
    } catch (e) {
      _addLog('Candle fetch error: $e', 'red');
    }
  }

  Future<void> disconnectFyers() async {
    try {
      await http.post(Uri.parse('$API_URL/auth/logout'));
      authenticated = false;
      running = false;
      _authUrl = null;
      _addLog('Disconnected from Fyers', 'amber');
      notifyListeners();
    } catch (e) {
      _addLog('Disconnect error: $e', 'red');
    }
  }

  Future<void> connectFyers() async {
    try {
      final res = await http.get(Uri.parse('$API_URL/auth/url'));
      final data = jsonDecode(res.body);
      _authUrl = data['auth_url'];
      notifyListeners();

      if (_authUrl != null) {
        final uri = Uri.parse(_authUrl!);
        // Actually open the Fyers login (new tab on web)
        if (await canLaunchUrl(uri)) {
          await launchUrl(uri, webOnlyWindowName: '_blank', mode: LaunchMode.externalApplication);
          _addLog('Fyers login opened in new tab', 'green');
        } else {
          _addLog('Copy the link below and open it manually', 'amber');
        }
      }
    } catch (e) {
      _addLog('Auth error: $e', 'red');
    }
  }

    String? _authUrl;
  String? get authUrl => _authUrl;

    @override
  void dispose() {
    _ws?.sink.close();
    super.dispose();
  }
}