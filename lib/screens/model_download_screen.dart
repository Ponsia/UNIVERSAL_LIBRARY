import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:unilib/screens/class_selection_screen.dart';
import 'package:unilib/services/rag_service.dart';
import 'package:unilib/services/sms_service.dart';

class ModelDownloadScreen extends StatefulWidget {
  const ModelDownloadScreen({super.key});

  @override
  State<ModelDownloadScreen> createState() => _ModelDownloadScreenState();
}

class _ModelDownloadScreenState extends State<ModelDownloadScreen> {
  final _token = TextEditingController();
  bool _hideToken = true;

  @override
  void initState() {
    super.initState();
    _loadSavedToken();
  }

  Future<void> _loadSavedToken() async {
    final prefs = await SharedPreferences.getInstance();
    final savedToken = prefs.getString('token') ?? SmsService.hfToken;
    setState(() {
      _token.text = savedToken;
    });
  }

  Future<void> _prepare() async {
    final rag = context.read<RagService>();
    try {
      await rag.prepareOffline(token: _token.text);
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => const ClassSelectionScreen(),
        ),
      );
    } on RagFailure catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.message),
            duration: const Duration(seconds: 8),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  @override
  void dispose() {
    _token.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final rag = context.watch<RagService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Download UniLib Lite'),
        centerTitle: true,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const Center(
              child: Icon(Icons.download_for_offline_rounded, size: 72, color: Color(0xFF1E88E5)),
            ),
            const SizedBox(height: 18),
            Text(
              'UniLib Lite • Offline Setup',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              'Enter your Hugging Face access token received via SMS to download the Gemma 3 1B model, EmbeddingGemma, and curriculum vector database onto your device.',
              textAlign: TextAlign.center,
              style: TextStyle(height: 1.4, color: Colors.grey),
            ),
            const SizedBox(height: 28),
            TextField(
              controller: _token,
              obscureText: _hideToken,
              enabled: !rag.isBusy,
              autocorrect: false,
              enableIMEPersonalizedLearning: false,
              enableSuggestions: false,
              decoration: InputDecoration(
                labelText: 'Hugging Face Access Token (hf_…)',
                helperText: 'Token was automatically received via SMS on your registered phone number.',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                prefixIcon: const Icon(Icons.vpn_key_rounded, color: Color(0xFF1E88E5)),
                suffixIcon: IconButton(
                  onPressed: () => setState(() => _hideToken = !_hideToken),
                  icon: Icon(
                    _hideToken ? Icons.visibility : Icons.visibility_off,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.blue.withValues(alpha: 0.2)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, color: Color(0xFF1E88E5), size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          rag.status,
                          key: const Key('rag_status'),
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                  if (rag.isBusy) ...[
                    const SizedBox(height: 12),
                    LinearProgressIndicator(
                      value: rag.progress > 0 ? rag.progress : null,
                      backgroundColor: Colors.blue.withValues(alpha: 0.1),
                      color: const Color(0xFF1E88E5),
                      minHeight: 6,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Please keep the app open while models and textbooks are indexed.',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 32),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF1E88E5),
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              onPressed: rag.isBusy
                  ? null
                  : rag.isReady
                      ? () => Navigator.pushReplacement(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const ClassSelectionScreen(),
                            ),
                          )
                      : _prepare,
              icon: Icon(rag.isReady ? Icons.check_circle_rounded : Icons.download_rounded),
              label: Text(
                rag.isReady ? 'Proceed to Secondary Classes' : 'Download and Setup UniLib',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

