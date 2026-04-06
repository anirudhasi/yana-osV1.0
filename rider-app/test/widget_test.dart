import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:yana_rider/app.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: YanaRiderApp()));
    await tester.pumpAndSettle();
    // App loads without crashing
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
