import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:unilib/main.dart';
import 'package:unilib/services/model_manager.dart';
import 'package:unilib/services/rag_service.dart';
import 'package:unilib/theme/theme_provider.dart';

void main() {
  testWidgets('App starts at login before offline setup', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => ThemeProvider()),
          ChangeNotifierProvider(create: (_) => ModelManager()),
          ChangeNotifierProvider(create: (_) => RagService()),
        ],
        child: const UniLibApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Welcome to UniLib'), findsOneWidget);
    expect(find.text('Sign In'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('Old download flag cannot bypass real offline setup', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({
      'isLoggedIn': true,
      'downloaded_model': 'lite',
      'model_path': '/old/qwen-as-gemma.gguf',
    });
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => ThemeProvider()),
          ChangeNotifierProvider(create: (_) => ModelManager()),
          ChangeNotifierProvider(create: (_) => RagService()),
        ],
        child: const UniLibApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Maandalizi ya TIE AI'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Pakua na andaa TIE AI'),
      250,
      scrollable: find
          .descendant(
            of: find.byType(ListView),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    await tester.pumpAndSettle();
    expect(find.text('Pakua na andaa TIE AI'), findsOneWidget);
    expect(find.text('UniLib Assistant'), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
