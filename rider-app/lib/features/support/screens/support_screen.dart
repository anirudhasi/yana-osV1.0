import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../providers/support_provider.dart';
import 'create_ticket_screen.dart';

class SupportScreen extends ConsumerWidget {
  const SupportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ticketsAsync = ref.watch(supportTicketsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Support')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const CreateTicketScreen()),
          );
          ref.invalidate(supportTicketsProvider);
        },
        icon: const Icon(Icons.add),
        label: const Text('New Ticket'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(supportTicketsProvider),
        child: ticketsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Error: $e')),
          data: (tickets) => tickets.isEmpty
              ? const Center(child: Text('No support tickets yet'))
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: tickets.length,
                  itemBuilder: (_, i) {
                    final t = tickets[i];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(t.subject),
                        subtitle: Text(
                          '${t.category.replaceAll('_', ' ')}  •  '
                          '${DateFormat('dd MMM yyyy').format(t.createdAt)}',
                        ),
                        trailing: _StatusChip(status: t.status),
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'OPEN' => Colors.blue,
      'IN_PROGRESS' => Colors.orange,
      'RESOLVED' => Colors.green,
      _ => Colors.grey,
    };
    return Chip(
      label: Text(status, style: TextStyle(color: color, fontSize: 11)),
      backgroundColor: color.withValues(alpha: 0.1),
      side: BorderSide(color: color.withValues(alpha: 0.3)),
      padding: EdgeInsets.zero,
    );
  }
}
