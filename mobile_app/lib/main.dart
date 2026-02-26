import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() {
  runApp(const SentinelWatcherApp());
}

class SentinelWatcherApp extends StatelessWidget {
  const SentinelWatcherApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Sentinel Auto-Trader',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF121212),
        primaryColor: const Color(0xFF1E88E5),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF1E88E5),
          secondary: Color(0xFF00E676),
          error: Color(0xFFFF5252),
        ),
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // TODO: Replace with actual production WS endpoint from Django Channels
  final String wsEndpoint = "ws://127.0.0.1:8000/ws/trades/";
  late WebSocketChannel _channel;
  
  // State variables from WebSocket
  double _totalEquity = 0.0;
  double _totalPnl = 0.0;
  List<dynamic> _activeTrades = [];
  bool _isConnected = false;

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  void _connectWebSocket() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(wsEndpoint));
      
      _channel.stream.listen(
        (message) {
          if (!mounted) return;
          setState(() {
            _isConnected = true;
          });
          
          try {
            final data = jsonDecode(message);
            if (data['type'] == 'portfolio_update') {
              setState(() {
                _totalEquity = (data['equity'] ?? 0).toDouble();
                _totalPnl = (data['pnl'] ?? 0).toDouble();
                _activeTrades = data['active_trades'] ?? [];
              });
            }
          } catch (e) {
            debugPrint("Parse error: $e");
          }
        },
        onError: (error) {
          setState(() => _isConnected = false);
          debugPrint("WebSocket Error: $error");
          // Reconnect logic would go here
        },
        onDone: () {
          setState(() => _isConnected = false);
        },
      );
    } catch (e) {
      setState(() => _isConnected = false);
    }
  }

  void _fireKillSwitch() {
    if (_isConnected) {
      _channel.sink.add(jsonEncode({"type": "kill_switch"}));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("KILL SWITCH ENGAGED. Halting all algorithmic execution..."),
          backgroundColor: Colors.redAccent,
        )
      );
    }
  }

  @override
  void dispose() {
    _channel.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Sentinel Ops", style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.black,
        elevation: 0,
        actions: [
          Icon(
            Icons.circle,
            color: _isConnected ? Colors.greenAccent : Colors.red,
            size: 14,
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Top Stats Card
            Container(
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: const Color(0xFF1E1E1E),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white12),
              ),
              child: Column(
                children: [
                  const Text(
                    "TOTAL PORTFOLIO EQUITY",
                    style: TextStyle(color: Colors.white54, fontSize: 12, letterSpacing: 1.5),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "\$${_totalEquity.toStringAsFixed(2)}",
                    style: const TextStyle(fontSize: 42, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        _totalPnl >= 0 ? Icons.arrow_upward : Icons.arrow_downward,
                        color: _totalPnl >= 0 ? Colors.greenAccent : Colors.redAccent,
                        size: 20
                      ),
                      const SizedBox(width: 4),
                      Text(
                        "\$${_totalPnl.abs().toStringAsFixed(2)}",
                        style: TextStyle(
                          fontSize: 20, 
                          color: _totalPnl >= 0 ? Colors.greenAccent : Colors.redAccent,
                          fontWeight: FontWeight.w600
                        ),
                      ),
                    ],
                  )
                ],
              ),
            ),
            
            // Active Trades List
            Expanded(
              child: _activeTrades.isEmpty
                  ? const Center(child: Text("No active trades", style: TextStyle(color: Colors.white54)))
                  : ListView.builder(
                      itemCount: _activeTrades.length,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemBuilder: (context, index) {
                        final t = _activeTrades[index];
                        final isBuy = t['side'] == 'buy';
                        return Card(
                          color: const Color(0xFF1E1E1E),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: isBuy ? Colors.green.withOpacity(0.2) : Colors.red.withOpacity(0.2),
                              child: Icon(
                                isBuy ? Icons.trending_up : Icons.trending_down,
                                color: isBuy ? Colors.greenAccent : Colors.redAccent,
                              ),
                            ),
                            title: Text("${t['symbol']} • ${t['quantity']} shares", style: const TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text("Price: \$${t['price']} | P&L: \$${t['pnl']}"),
                            trailing: Text(t['strategy'], style: const TextStyle(color: Colors.white54, fontSize: 12)),
                          ),
                        );
                      },
                    ),
            ),
            
            // Panic Button
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              child: InkWell(
                onTap: () {
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      backgroundColor: const Color(0xFF2A2A2A),
                      title: const Text("ENGAGE KILL SWITCH?", style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold)),
                      content: const Text("This will immediately close ALL open positions across ALL prop firm accounts at market price and halt the strategy runner."),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx),
                          child: const Text("CANCEL", style: TextStyle(color: Colors.white54)),
                        ),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                          onPressed: () {
                            Navigator.pop(ctx);
                            _fireKillSwitch();
                          },
                          child: const Text("EXECUTE"),
                        ),
                      ],
                    )
                  );
                },
                child: Container(
                  height: 80,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: Colors.redAccent.withOpacity(0.1),
                    border: Border.all(color: Colors.redAccent, width: 2),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Center(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 32),
                        SizedBox(width: 12),
                        Text(
                          "EMERGENCY KILL SWITCH",
                          style: TextStyle(
                            color: Colors.redAccent,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            )
          ],
        ),
      ),
    );
  }
}
