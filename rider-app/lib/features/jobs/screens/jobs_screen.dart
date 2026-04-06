import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../models/job_models.dart';
import '../providers/jobs_provider.dart';
import 'job_detail_screen.dart';

class JobsScreen extends ConsumerWidget {
  const JobsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final slotsAsync = ref.watch(publishedSlotsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Available Jobs')),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(publishedSlotsProvider),
        child: slotsAsync.when(
          loading: () =>
              const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(child: Text('Error: $e')),
          data: (slots) => slots.isEmpty
              ? const Center(child: Text('No jobs available right now'))
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: slots.length,
                  itemBuilder: (_, i) => _SlotCard(slot: slots[i]),
                ),
        ),
      ),
    );
  }
}

class _SlotCard extends StatelessWidget {
  final JobSlot slot;
  const _SlotCard({required this.slot});

  @override
  Widget build(BuildContext context) {
    final timeFmt = DateFormat('hh:mm a');
    final dateFmt = DateFormat('EEE, dd MMM');
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => JobDetailScreen(slot: slot)),
        ),
        title: Text(slot.clientName,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(slot.darkStoreName),
            Text(
                '${dateFmt.format(slot.startTime)}  •  ${timeFmt.format(slot.startTime)} – ${timeFmt.format(slot.endTime)}'),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text('₹${slot.payoutAmount.toStringAsFixed(0)}',
                style: const TextStyle(
                    fontWeight: FontWeight.bold, fontSize: 16)),
            const Text('payout', style: TextStyle(fontSize: 11, color: Colors.grey)),
          ],
        ),
        isThreeLine: true,
      ),
    );
  }
}
