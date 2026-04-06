// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'support_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

String _$supportTicketsHash() => r'3714ef05e0d4c43230f4a6690ea9a08699d1142f';

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
// ignore: unused_element
typedef SupportTicketsRef = AutoDisposeFutureProviderRef<List<SupportTicket>>;
String _$supportCategoriesHash() => r'a20d2f3daf9e003b8d9daf446cd970c322f23a3c';

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
// ignore: unused_element
typedef SupportCategoriesRef
    = AutoDisposeFutureProviderRef<List<SupportCategory>>;
String _$createTicketHash() => r'6aa1bb89df1a280bae0e89a3502313caec6707e9';

/// See also [CreateTicket].
@ProviderFor(CreateTicket)
final createTicketProvider = AutoDisposeNotifierProvider<CreateTicket,
    AsyncValue<SupportTicket?>>.internal(
  CreateTicket.new,
  name: r'createTicketProvider',
  debugGetCreateSourceHash:
      const bool.fromEnvironment('dart.vm.product') ? null : _$createTicketHash,
  dependencies: null,
  allTransitiveDependencies: null,
);

typedef _$CreateTicket = AutoDisposeNotifier<AsyncValue<SupportTicket?>>;
// ignore_for_file: type=lint
// ignore_for_file: subtype_of_sealed_class, invalid_use_of_internal_member, invalid_use_of_visible_for_testing_member, deprecated_member_use_from_same_package
