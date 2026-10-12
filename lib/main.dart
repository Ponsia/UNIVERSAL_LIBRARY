import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:unilib/screens/auth_screen.dart';
import 'package:unilib/theme/app_theme.dart';
import 'package:unilib/theme/theme_provider.dart';
import 'package:unilib/services/model_manager.dart';
import 'package:unilib/services/rag_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Load the screened TIE corpus and restore the installed offline models.
  final ragService = RagService();
  try {
    await ragService.initKnowledgeBase();
  } catch (e) {
    debugPrint("Error initializing KnowledgeBase: $e");
  }

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => ModelManager()),
        ChangeNotifierProvider.value(value: ragService),
      ],
      child: const UniLibApp(),
    ),
  );
}

class UniLibApp extends StatelessWidget {
  const UniLibApp({super.key});

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return MaterialApp(
      title: 'UniLib',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeProvider.themeMode,
      debugShowCheckedModeBanner: false,
      home: const AuthScreen(),
    );
  }
}
