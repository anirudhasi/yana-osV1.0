import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../core/storage/token_storage.dart';
import '../data/support_repository.dart';
import '../models/support_models.dart';

part 'support_provider.g.dart';

@riverpod
Future<List<SupportTicket>> supportTickets(Ref ref) async {
  final storage = ref.watch(tokenStorageProvider);
  final riderId = await storage.getRiderId() ?? '';
  return ref.watch(supportRepositoryProvider).fetchTickets(riderId);
}

@riverpod
Future<List<SupportCategory>> supportCategories(Ref ref) async {
  return ref.watch(supportRepositoryProvider).getCategories();
}

@riverpod
class CreateTicket extends _$CreateTicket {
  @override
  AsyncValue<SupportTicket?> build() => const AsyncData(null);

  Future<void> submit({
    required String category,
    required String subject,
    required String description,
  }) async {
    state = const AsyncLoading();
    final storage = ref.read(tokenStorageProvider);
    final riderId = await storage.getRiderId() ?? '';
    state = await AsyncValue.guard(
      () => ref.read(supportRepositoryProvider).createTicket(
            riderId: riderId,
            category: category,
            subject: subject,
            description: description,
          ),
    );
    if (!state.hasError) ref.invalidate(supportTicketsProvider);
  }
}
