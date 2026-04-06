import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../../core/network/dio_client.dart';
import '../models/support_models.dart';

part 'support_repository.g.dart';

class SupportRepository {
  final Dio _dio;
  const SupportRepository(this._dio);

  Future<List<SupportTicket>> fetchTickets(String riderId) async {
    final res =
        await _dio.get('/api/v1/support/riders/$riderId/tickets/');
    final list =
        (res.data['data']?['results'] ?? res.data['data'] ?? []) as List;
    return list
        .map((e) => SupportTicket.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<SupportTicket> createTicket({
    required String riderId,
    required String category,
    required String subject,
    required String description,
  }) async {
    final res = await _dio.post(
      '/api/v1/support/tickets/',
      data: {
        'category': category,
        'subject': subject,
        'description': description,
      },
    );
    return SupportTicket.fromJson(res.data['data'] as Map<String, dynamic>);
  }

  List<SupportCategory> getCategories() => const [
        SupportCategory('VEHICLE_ISSUE', 'Vehicle Issue'),
        SupportCategory('PAYMENT_ISSUE', 'Payment Issue'),
        SupportCategory('CUSTOMER_COMPLAINT', 'Customer Complaint'),
        SupportCategory('APP_ISSUE', 'App Issue'),
        SupportCategory('KYC_QUERY', 'KYC Query'),
        SupportCategory('GENERAL', 'General'),
        SupportCategory('OTHER', 'Other'),
      ];
}

@riverpod
SupportRepository supportRepository(Ref ref) =>
    SupportRepository(ref.watch(dioClientProvider));
