class JobSlot {
  final String id;
  final String clientName;
  final String darkStoreName;
  final String city;
  final DateTime startTime;
  final DateTime endTime;
  final double payoutAmount;
  final String status;

  const JobSlot({
    required this.id,
    required this.clientName,
    required this.darkStoreName,
    required this.city,
    required this.startTime,
    required this.endTime,
    required this.payoutAmount,
    required this.status,
  });

  factory JobSlot.fromJson(Map<String, dynamic> json) => JobSlot(
        id: json['id'] as String? ?? '',
        clientName: (json['client'] as Map<String, dynamic>?)?['name'] as String? ?? '',
        darkStoreName:
            (json['dark_store'] as Map<String, dynamic>?)?['name'] as String? ?? '',
        city: (json['dark_store'] as Map<String, dynamic>?)?['city'] as String? ?? '',
        startTime:
            DateTime.tryParse(json['start_time'] as String? ?? '') ?? DateTime.now(),
        endTime:
            DateTime.tryParse(json['end_time'] as String? ?? '') ?? DateTime.now(),
        payoutAmount: (json['payout_amount'] as num?)?.toDouble() ?? 0.0,
        status: json['status'] as String? ?? 'PUBLISHED',
      );
}
