// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'support_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$supportTicketsHash() => r'support_tickets_provider_hash';
String _$supportCategoriesHash() => r'support_categories_provider_hash';
String _$createTicketHash() => r'create_ticket_notifier_hash';

/// See also [supportTickets].
@ProviderFor(supportTickets)
final supportTicketsProvider =
    AutoDisposeFutureProvider<List<SupportTicket>>.internal(
  supportTickets,
  name: r'supportTicketsProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$supportTicketsHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
typedef SupportTicketsRef = AutoDisposeFutureProviderRef<List<SupportTicket>>;

/// See also [supportCategories].
@ProviderFor(supportCategories)
final supportCategoriesProvider =
    AutoDisposeFutureProvider<List<SupportCategory>>.internal(
  supportCategories,
  name: r'supportCategoriesProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$supportCategoriesHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

@Deprecated('Will be removed in 3.0. Use Ref instead')
typedef SupportCategoriesRef =
    AutoDisposeFutureProviderRef<List<SupportCategory>>;

/// See also [CreateTicket].
@ProviderFor(CreateTicket)
final createTicketProvider = AutoDisposeNotifierProvider<CreateTicket,
    AsyncValue<SupportTicket?>>.internal(
  CreateTicket.new,
  name: r'createTicketProvider',
  debugGetCreateSourceHash: const bool.fromEnvironment('dart.vm.product')
      ? null
      : _$createTicketHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$CreateTicket = AutoDisposeNotifier<AsyncValue<SupportTicket?>>;
