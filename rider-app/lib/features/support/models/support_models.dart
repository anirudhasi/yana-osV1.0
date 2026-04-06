class SupportTicket {
  final String id;
  final String ticketNumber;
  final String category;
  final String subject;
  final String description;
  final String status;
  final String priority;
  final DateTime createdAt;

  const SupportTicket({
    required this.id,
    required this.ticketNumber,
    required this.category,
    required this.subject,
    required this.description,
    required this.status,
    required this.priority,
    required this.createdAt,
  });

  factory SupportTicket.fromJson(Map<String, dynamic> json) => SupportTicket(
        id: json['id'] as String? ?? '',
        ticketNumber: json['ticket_number'] as String? ?? '',
        category: json['category'] as String? ?? '',
        subject: json['subject'] as String? ?? '',
        description: json['description'] as String? ?? '',
        status: json['status'] as String? ?? 'OPEN',
        priority: json['priority'] as String? ?? 'MEDIUM',
        createdAt:
            DateTime.tryParse(json['created_at'] as String? ?? '') ??
                DateTime.now(),
      );
}

class SupportCategory {
  final String value;
  final String label;

  const SupportCategory(this.value, this.label);
}
