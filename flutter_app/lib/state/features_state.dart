import 'package:flutter/foundation.dart';
import '../services/features_api.dart';

class FeaturesState extends ChangeNotifier {
  bool loading = false;
  String? error;

  Map<String, dynamic> dashboard = {};
  List<dynamic> watchlist = [];
  Map<String, dynamic> portfolio = {};
  Map<String, dynamic> portfolioAdvisor = {};
  List<dynamic> news = [];
  Map<String, dynamic> options = {};
  Map<String, dynamic> paperAccount = {};
  List<dynamic> paperTrades = [];
  List<dynamic> alerts = [];
  List<dynamic> screenerResults = [];
  Map<String, dynamic> technical = {};
  Map<String, dynamic> aiAnalysis = {};
  List<dynamic> journal = [];
  Map<String, dynamic> journalAi = {};

  Future<void> loadDashboard() async {
    await _run(() async => dashboard = Map<String, dynamic>.from(await FeaturesApi.get('/market/dashboard')));
  }

  Future<void> loadWatchlist() async {
    await _run(() async => watchlist = List.from(await FeaturesApi.get('/watchlist')));
  }

  Future<void> addWatchlist(String symbol) async {
    await FeaturesApi.post('/watchlist', {'symbol': symbol.toUpperCase()});
    await loadWatchlist();
  }

  Future<void> loadPortfolio() async {
    await _run(() async {
      portfolio = Map<String, dynamic>.from(await FeaturesApi.get('/portfolio'));
      portfolioAdvisor = Map<String, dynamic>.from(await FeaturesApi.get('/portfolio/advisor'));
    });
  }

  Future<void> addHolding(String symbol, double qty, double price) async {
    await FeaturesApi.post('/portfolio/holdings', {'symbol': symbol, 'qty': qty, 'avg_price': price});
    await loadPortfolio();
  }

  Future<void> loadNews() async {
    await _run(() async => news = List.from(await FeaturesApi.get('/news?limit=20')));
  }

  Future<void> loadOptions() async {
    await _run(() async => options = Map<String, dynamic>.from(await FeaturesApi.get('/options')));
  }

  Future<void> loadPaper() async {
    await _run(() async {
      paperAccount = Map<String, dynamic>.from(await FeaturesApi.get('/paper/account'));
      paperTrades = List.from(await FeaturesApi.get('/paper/trades?limit=30'));
    });
  }

  Future<Map<String, dynamic>> paperBuy(String symbol, int qty) async {
    final r = await FeaturesApi.post('/paper/buy', {'symbol': symbol, 'qty': qty});
    await loadPaper();
    return Map<String, dynamic>.from(r);
  }

  Future<void> loadAlerts() async {
    await _run(() async => alerts = List.from(await FeaturesApi.get('/alerts')));
  }

  Future<void> runScreener(String preset) async {
    await _run(() async => screenerResults = List.from(await FeaturesApi.get('/screener/preset/$preset')));
  }

  Future<void> loadTechnical(String symbol) async {
    await _run(() async => technical = Map<String, dynamic>.from(await FeaturesApi.get('/technical/${symbol.toUpperCase()}')));
  }

  Future<void> analyzeStock(String symbol, {String question = ''}) async {
    await _run(() async => aiAnalysis = Map<String, dynamic>.from(
      await FeaturesApi.post('/ai/analyze', {'symbol': symbol.toUpperCase(), 'question': question}),
    ));
  }

  Future<void> loadJournal() async {
    await _run(() async {
      journal = List.from(await FeaturesApi.get('/journal?limit=30'));
      journalAi = Map<String, dynamic>.from(await FeaturesApi.get('/journal/ai-analysis'));
    });
  }

  Future<void> _run(Future<void> Function() fn) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      await fn();
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }
}
