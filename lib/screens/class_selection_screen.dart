import 'package:flutter/material.dart';
import 'package:unilib/screens/chat_screen.dart';
import 'package:unilib/services/model_manager.dart';

class ClassSelectionScreen extends StatelessWidget {
  const ClassSelectionScreen({super.key});

  final List<Map<String, dynamic>> classes = const [
    {
      'title': 'Form One (Form 1)',
      'level': 'O-Level Secondary',
      'books': 'Biology, Chemistry & Physics',
      'chunks': '451 Chunks Embedded',
      'icon': Icons.menu_book_rounded,
      'isAvailable': true,
      'color': Color(0xFF1E88E5),
    },
    {
      'title': 'Form Two (Form 2)',
      'level': 'O-Level Secondary',
      'books': 'Textbooks pending OCR & embedding',
      'chunks': '0 Chunks',
      'icon': Icons.lock_outline_rounded,
      'isAvailable': false,
      'color': Colors.grey,
    },
    {
      'title': 'Form Three (Form 3)',
      'level': 'O-Level Secondary',
      'books': 'Textbooks pending OCR & embedding',
      'chunks': '0 Chunks',
      'icon': Icons.lock_outline_rounded,
      'isAvailable': false,
      'color': Colors.grey,
    },
    {
      'title': 'Form Four (Form 4)',
      'level': 'O-Level Secondary',
      'books': 'Textbooks pending OCR & embedding',
      'chunks': '0 Chunks',
      'icon': Icons.lock_outline_rounded,
      'isAvailable': false,
      'color': Colors.grey,
    },
    {
      'title': 'Form Five (Form 5)',
      'level': 'A-Level Secondary',
      'books': 'Advanced curriculum pending embedding',
      'chunks': '0 Chunks',
      'icon': Icons.lock_outline_rounded,
      'isAvailable': false,
      'color': Colors.grey,
    },
    {
      'title': 'Form Six (Form 6)',
      'level': 'A-Level Secondary',
      'books': 'Advanced curriculum pending embedding',
      'chunks': '0 Chunks',
      'icon': Icons.lock_outline_rounded,
      'isAvailable': false,
      'color': Colors.grey,
    },
  ];

  void _onClassSelected(BuildContext context, Map<String, dynamic> classItem) {
    if (classItem['isAvailable'] == true) {
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) {
          return AlertDialog(
            title: Row(
              children: const [
                Icon(Icons.check_circle_outline, color: Color(0xFF1E88E5)),
                SizedBox(width: 10),
                Text('Form 1 Textbooks'),
              ],
            ),
            content: const Text(
              'Form One Curriculum verified!\n\n• Biology Form One (TIE)\n• Chemistry Form One (TIE)\n• Physics Form One (TIE)\n\nOpening UniLib Assistant...',
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ChatScreen(selectedModel: ModelManager.tieModel),
                    ),
                  );
                },
                child: const Text('Continue to Chat'),
              ),
            ],
          );
        },
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${classItem['title']} textbooks are coming soon. Only Form 1 is active for offline learning.'),
          duration: const Duration(seconds: 3),
          backgroundColor: Colors.orange[800],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Secondary Study Levels'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
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
                  Icon(Icons.school_rounded, color: Color(0xFF1E88E5), size: 36),
                  SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Select Your Class Level',
                          style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Choose secondary level from Form 1 to Form 6 to load embedded textbooks.',
                          style: TextStyle(fontSize: 13, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            ...classes.map((c) {
              final isAvail = c['isAvailable'] as bool;
              final Color primaryColor = c['color'] as Color;

              return Card(
                elevation: isAvail ? 3 : 1,
                margin: const EdgeInsets.only(bottom: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                  side: BorderSide(
                    color: isAvail ? primaryColor.withValues(alpha: 0.5) : Colors.transparent,
                    width: isAvail ? 1.5 : 1,
                  ),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: () => _onClassSelected(context, c),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: primaryColor.withValues(alpha: isAvail ? 0.15 : 0.08),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(c['icon'] as IconData, color: primaryColor, size: 28),
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
                                      c['title'] as String,
                                      style: TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                        color: isAvail ? (isDark ? Colors.white : Colors.black87) : Colors.grey,
                                      ),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: isAvail ? Colors.green.withValues(alpha: 0.15) : Colors.grey.withValues(alpha: 0.15),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      isAvail ? 'Active' : 'Coming Soon',
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: isAvail ? Colors.green[700] : Colors.grey[600],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 6),
                              Text(
                                c['books'] as String,
                                style: TextStyle(
                                  fontSize: 13,
                                  color: isDark ? Colors.white70 : Colors.black54,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                c['chunks'] as String,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: isAvail ? const Color(0xFF1E88E5) : Colors.grey,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Icon(
                          Icons.arrow_forward_ios_rounded,
                          size: 16,
                          color: isAvail ? const Color(0xFF1E88E5) : Colors.grey,
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

