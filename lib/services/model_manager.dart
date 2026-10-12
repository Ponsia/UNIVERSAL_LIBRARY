import 'package:flutter/material.dart';

class AIModelInfo {
  final String id;
  final String name;
  final String description;
  final IconData icon;
  final Color color;

  AIModelInfo({
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
    required this.color,
  });
}

class ModelManager extends ChangeNotifier {
  static final tieModel = unilibLite;

  static final unilibLite = AIModelInfo(
    id: 'lite',
    name: 'Unilib Lite',
    description: 'Offline Edge AI (Gemma 3 1B) • Form 1 Books',
    icon: Icons.flash_on_rounded,
    color: const Color(0xFF1E88E5),
  );

  static final unilibPro = AIModelInfo(
    id: 'pro',
    name: 'Unilib Pro',
    description: 'Medium SLM for Multimodal Reasoning (Coming Soon)',
    icon: Icons.psychology_rounded,
    color: Colors.purple,
  );

  static final unilibMax = AIModelInfo(
    id: 'max',
    name: 'Unilib Max',
    description: 'Large Edge AI Model for Code & Image Generation (Coming Soon)',
    icon: Icons.rocket_launch_rounded,
    color: Colors.orange,
  );

  static final List<AIModelInfo> allModels = [unilibLite, unilibPro, unilibMax];
}
