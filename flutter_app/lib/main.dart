import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'state/bot_state.dart';
import 'state/mcp_state.dart';
import 'state/features_state.dart';
import 'screens/dashboard_screen.dart';
import 'screens/journal_screen.dart';
import 'screens/mcp_screen.dart';
import 'screens/markets_hub_screen.dart';
import 'screens/settings_screen.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => BotState()..connect()),
        ChangeNotifierProvider(create: (_) => McpState()),
        ChangeNotifierProvider(create: (_) => FeaturesState()),
      ],
      child: const NiftyApp(),
    ),
  );
}

class NiftyApp extends StatelessWidget {
  const NiftyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Nifty AI Bot',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF050608),
        primaryColor: const Color(0xFF00D97E),
        fontFamily: 'monospace',
      ),
      home: const HomeShell(),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  final _pages = [
    const DashboardScreen(),
    const MarketsHubScreen(),
    const JournalScreen(),
    const McpScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_index],
      bottomNavigationBar: BottomNavigationBar(
        backgroundColor: const Color(0xFF0A0C10),
        currentIndex: _index,
        onTap: (i) => setState(() => _index = i),
        selectedItemColor: const Color(0xFF00D97E),
        unselectedItemColor: const Color(0xFF4A4F62),
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dashboard_outlined), label: 'Bot'),
          BottomNavigationBarItem(icon: Icon(Icons.candlestick_chart_outlined), label: 'Markets'),
          BottomNavigationBarItem(icon: Icon(Icons.history), label: 'Journal'),
          BottomNavigationBarItem(icon: Icon(Icons.smart_toy_outlined), label: 'AI'),
          BottomNavigationBarItem(icon: Icon(Icons.settings_outlined), label: 'Settings'),
        ],
      ),
    );
  }
}
