import 'package:flutter/material.dart';
import 'package:unilib/screens/model_download_screen.dart';
import 'package:unilib/services/model_manager.dart';

class ModelSelectionScreen extends StatelessWidget {
  const ModelSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final models = [
      {
        'model': ModelManager.unilibLite,
        'badge': 'Active • Ready',
        'badgeColor': Colors.green,
        'details': 'Google Gemma 3 1B + EmbeddingGemma 300M\nOptimized for Secondary Education (Form 1 - Form 6)',
        'enabled': true,
      },
      {
        'model': ModelManager.unilibPro,
        'badge': 'Coming Soon',
        'badgeColor': Colors.grey,
        'details': 'Medium Multimodal SLM\nFor Advanced Graphical & Diagram Analysis',
        'enabled': false,
      },
      {
        'model': ModelManager.unilibMax,
        'badge': 'Coming Soon',
        'badgeColor': Colors.grey,
        'details': 'Large High-Precision Edge Model\nFor Deep Multi-turn Reasoning, Code & Image Generation',
        'enabled': false,
      },
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Select UniLib AI Model'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E88E5).withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFF1E88E5).withValues(alpha: 0.2)),
              ),
              child: Row(
                children: const [
                  Icon(Icons.psychology_rounded, color: Color(0xFF1E88E5), size: 36),
                  SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Choose Your AI Engine',
                          style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'UniLib Lite is active for current offline learning. Pro and Max are in preview.',
                          style: TextStyle(fontSize: 13, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            ...models.map((item) {
              final AIModelInfo model = item['model'] as AIModelInfo;
              final bool enabled = item['enabled'] as bool;
              final Color badgeColor = item['badgeColor'] as Color;
              final String badge = item['badge'] as String;
              final String details = item['details'] as String;

              return Card(
                elevation: enabled ? 3 : 1,
                margin: const EdgeInsets.only(bottom: 18),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18),
                  side: BorderSide(
                    color: enabled ? model.color.withValues(alpha: 0.6) : Colors.transparent,
                    width: enabled ? 1.5 : 1,
                  ),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(18),
                  onTap: () {
                    if (enabled) {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => const ModelDownloadScreen(),
                        ),
                      );
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('${model.name} is in development. Please select UniLib Lite to proceed.'),
                          backgroundColor: Colors.orange[800],
                          duration: const Duration(seconds: 3),
                        ),
                      );
                    }
                  },
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: model.color.withValues(alpha: enabled ? 0.15 : 0.08),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Icon(model.icon, color: model.color, size: 30),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          model.name,
                                          style: TextStyle(
                                            fontSize: 17,
                                            fontWeight: FontWeight.bold,
                                            color: enabled
                                                ? (isDark ? Colors.white : Colors.black87)
                                                : Colors.grey,
                                          ),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: badgeColor.withValues(alpha: 0.15),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Text(
                                          badge,
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                            color: badgeColor,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    model.description,
                                    style: TextStyle(
                                      fontSize: 13,
                                      color: isDark ? Colors.white70 : Colors.black54,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        const Divider(height: 1, color: Colors.transparent),
                        const SizedBox(height: 12),
                        Text(
                          details,
                          style: TextStyle(
                            fontSize: 12,
                            height: 1.4,
                            color: isDark ? Colors.white54 : Colors.grey[600],
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            Text(
                              enabled ? 'Configure & Download' : 'Preview Only',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: enabled ? const Color(0xFF1E88E5) : Colors.grey,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Icon(
                              Icons.arrow_forward_rounded,
                              size: 16,
                              color: enabled ? const Color(0xFF1E88E5) : Colors.grey,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
