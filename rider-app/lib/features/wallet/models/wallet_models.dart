class Wallet {
  final String riderId;
  final double balance;
  final String currency;

  const Wallet({
    required this.riderId,
    required this.balance,
    required this.currency,
  });

  factory Wallet.fromJson(Map<String, dynamic> json) => Wallet(
        riderId: json['rider_id'] as String? ?? '',
        balance: (json['balance'] as num?)?.toDouble() ?? 0.0,
        currency: json['currency'] as String? ?? 'INR',
      );
}

class LedgerEntry {
  final String id;
  final String description;
  final double amount;
  final String direction; // C or D
  final String paymentType;
  final DateTime createdAt;

  const LedgerEntry({
    required this.id,
    required this.description,
    required this.amount,
    required this.direction,
    required this.paymentType,
    required this.createdAt,
  });

  factory LedgerEntry.fromJson(Map<String, dynamic> json) => LedgerEntry(
        id: json['id'] as String? ?? '',
        description: json['description'] as String? ?? '',
        amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
        direction: json['direction'] as String? ?? 'C',
        paymentType: json['payment_type'] as String? ?? '',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ??
            DateTime.now(),
      );
}
