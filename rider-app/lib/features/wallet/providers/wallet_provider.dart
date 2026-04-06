import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/storage/token_storage.dart';
import '../data/wallet_repository.dart';
import '../models/wallet_models.dart';

final walletProvider = FutureProvider<Wallet>((ref) async {
  final storage = ref.watch(tokenStorageProvider);
  final riderId = await storage.getRiderId() ?? '';
  final repo = ref.watch(walletRepositoryProvider);
  return repo.fetchWallet(riderId);
});

final ledgerProvider = FutureProvider<List<LedgerEntry>>((ref) async {
  final storage = ref.watch(tokenStorageProvider);
  final riderId = await storage.getRiderId() ?? '';
  final repo = ref.watch(walletRepositoryProvider);
  return repo.fetchLedger(riderId);
});
