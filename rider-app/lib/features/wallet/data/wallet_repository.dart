import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/dio_client.dart';
import '../models/wallet_models.dart';

class WalletRepository {
  final Dio _dio;
  const WalletRepository(this._dio);

  Future<Wallet> fetchWallet(String riderId) async {
    final res = await _dio.get('/api/v1/payments/wallets/$riderId/');
    return Wallet.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  Future<List<LedgerEntry>> fetchLedger(String riderId) async {
    final res =
        await _dio.get('/api/v1/payments/wallets/$riderId/ledger/');
    final list = res.data['data'] as List? ?? [];
    return list.map((e) => LedgerEntry.fromJson(e as Map<String, dynamic>)).toList();
  }
}

final walletRepositoryProvider = Provider<WalletRepository>(
  (ref) => WalletRepository(ref.watch(dioClientProvider)),
);
