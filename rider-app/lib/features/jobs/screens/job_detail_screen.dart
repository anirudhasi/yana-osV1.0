import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../models/job_models.dart';
import '../providers/jobs_provider.dart';

class JobDetailScreen extends ConsumerWidget {
  final JobSlot slot;
  const JobDetailScreen({super.key, required this.slot});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final applyState = ref.watch(applyProvider);
    final dateFmt = DateFormat('EEE, dd MMM yyyy');
    final timeFmt = DateFormat('hh:mm a');

    return Scaffold(
      appBar: AppBar(title: const Text('Job Details')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _InfoRow('Client', slot.clientName),
          _InfoRow('Location', slot.darkStoreName),
          _InfoRow('City', slot.city),
          _InfoRow('Date', dateFmt.format(slot.startTime)),
          _InfoRow('Time',
              '${timeFmt.format(slot.startTime)} – ${timeFmt.format(slot.endTime)}'),
          _InfoRow('Payout', '₹${slot.payoutAmount.toStringAsFixed(2)}'),
          const SizedBox(height: 32),
          if (applyState.hasError)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text('Error: ${applyState.error}',
                  style: const TextStyle(color: Colors.red)),
            ),
          FilledButton(
            onPressed: applyState.isLoading
                ? null
                : () async {
                    await ref.read(applyProvider.notifier).apply(slot.id);
                    if (context.mounted) Navigator.of(context).pop();
                  },
            child: applyState.isLoading
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Apply for this Job'),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(label,
                style: const TextStyle(color: Colors.grey, fontSize: 13)),
          ),
          Expanded(
            child: Text(value,
                style: const TextStyle(fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }
}
