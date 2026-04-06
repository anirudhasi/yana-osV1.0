import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/jobs_repository.dart';
import '../models/job_models.dart';

final publishedSlotsProvider = FutureProvider<List<JobSlot>>((ref) {
  final repo = ref.watch(jobsRepositoryProvider);
  return repo.fetchPublishedSlots();
});

class ApplyNotifier extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> apply(String slotId) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(jobsRepositoryProvider).applyToSlot(slotId),
    );
    if (!state.hasError) {
      ref.invalidate(publishedSlotsProvider);
    }
  }
}

final applyProvider =
    AsyncNotifierProvider<ApplyNotifier, void>(ApplyNotifier.new);
