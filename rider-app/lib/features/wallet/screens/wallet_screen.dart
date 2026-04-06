import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../providers/wallet_provider.dart';

class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final walletAsync = ref.watch(walletProvider);
    final ledgerAsync = ref.watch(ledgerProvider);
    final fmt = NumberFormat.currency(locale: 'en_IN', symbol: '₹');

    return Scaffold(
      appBar: AppBar(title: const Text('Wallet')),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(walletProvider);
          ref.invalidate(ledgerProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            walletAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Text('Error: $e'),
              data: (wallet) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    children: [
                      const Text('Available Balance',
                          style: TextStyle(color: Colors.grey)),
                      const SizedBox(height: 8),
                      Text(
                        fmt.format(wallet.balance),
                        style: const TextStyle(
                            fontSize: 36, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text('Transactions',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            ledgerAsync.when(
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (e, _) => Text('Error loading transactions: $e'),
              data: (entries) => entries.isEmpty
                  ? const Center(child: Text('No transactions yet'))
                  : Column(
                      children: entries
                          .map((e) => ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: e.direction == 'C'
                                      ? Colors.green[100]
                                      : Colors.red[100],
                                  child: Icon(
                                    e.direction == 'C'
                                        ? Icons.arrow_downward
                                        : Icons.arrow_upward,
                                    color: e.direction == 'C'
                                        ? Colors.green
                                        : Colors.red,
                                  ),
                                ),
                                title: Text(e.description),
                                subtitle: Text(
                                  DateFormat('dd MMM yyyy').format(e.createdAt),
                                ),
                                trailing: Text(
                                  '${e.direction == 'C' ? '+' : '-'}${fmt.format(e.amount)}',
                                  style: TextStyle(
                                    color: e.direction == 'C'
                                        ? Colors.green
                                        : Colors.red,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ))
                          .toList(),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
