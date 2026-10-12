import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:unilib/services/model_manager.dart';
import 'package:unilib/services/rag_service.dart';
import 'package:unilib/screens/auth_screen.dart';
import 'package:unilib/theme/theme_provider.dart';
import 'package:unilib/screens/model_selection_screen.dart';
import 'package:unilib/screens/class_selection_screen.dart';

class ChatScreen extends StatefulWidget {
  final AIModelInfo selectedModel;

  const ChatScreen({super.key, required this.selectedModel});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();
  final FlutterTts _flutterTts = FlutterTts();
  late stt.SpeechToText _speech;

  bool _isListening = false;
  int? _speakingMessageIndex;
  bool _isTyping = false;
  late AIModelInfo _currentModel;
  String _currentVoiceModel = "Default English (US)";

  List<Map<String, dynamic>> _messages = [];
  List<Map<String, dynamic>> _savedSessions = [];
  String _currentSessionId = DateTime.now().millisecondsSinceEpoch.toString();
  String _userName = "Student";

  @override
  void initState() {
    super.initState();
    _currentModel = widget.selectedModel;
    _speech = stt.SpeechToText();
    _initTts();
    _loadUserData();
  }

  void _loadUserData() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _userName = prefs.getString('username') ?? "Student";
    });
    _loadChatHistory(prefs);
  }

  void _loadChatHistory(SharedPreferences prefs) {
    List<String> sessions = prefs.getStringList('chat_sessions') ?? [];
    List<Map<String, dynamic>> loadedSessions = [];
    for (String sessionId in sessions) {
      String? sessionData = prefs.getString('chat_session_$sessionId');
      if (sessionData != null) {
        List<dynamic> msgs = jsonDecode(sessionData);
        String title = "Study Session";
        if (msgs.isNotEmpty) {
          var firstUserMsg = msgs.firstWhere(
            (m) => m["role"] == "user",
            orElse: () => null,
          );
          if (firstUserMsg != null) {
            title = firstUserMsg["content"].toString();
            if (title.length > 30) title = '${title.substring(0, 30)}...';
          }
        }
        loadedSessions.add({"id": sessionId, "title": title, "messages": msgs});
      }
    }
    if (!mounted) return;
    setState(() {
      _savedSessions = loadedSessions.reversed.toList();
    });
  }

  void _saveCurrentSession() async {
    if (_messages.isEmpty) return;
    final sessionId = _currentSessionId;
    final snapshot = jsonEncode(_messages);
    SharedPreferences prefs = await SharedPreferences.getInstance();
    List<String> sessions = prefs.getStringList('chat_sessions') ?? [];
    if (!sessions.contains(sessionId)) {
      sessions.add(sessionId);
      await prefs.setStringList('chat_sessions', sessions);
    }
    await prefs.setString('chat_session_$sessionId', snapshot);
    _loadChatHistory(prefs);
  }

  void _deleteSession(String sessionId) async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    List<String> sessions = prefs.getStringList('chat_sessions') ?? [];
    sessions.remove(sessionId);
    await prefs.setStringList('chat_sessions', sessions);
    await prefs.remove('chat_session_$sessionId');
    if (_currentSessionId == sessionId) {
      setState(() {
        _messages.clear();
        _currentSessionId = DateTime.now().millisecondsSinceEpoch.toString();
      });
    }
    _loadChatHistory(prefs);
  }

  void _loadSession(String sessionId, List<dynamic> messages) {
    setState(() {
      _currentSessionId = sessionId;
      _messages = List<Map<String, dynamic>>.from(messages);
    });
    Navigator.pop(context);
    _scrollToBottom();
  }

  void _initTts() async {
    await _flutterTts.setLanguage("en-US");
    await _flutterTts.setSpeechRate(0.4);
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);
    _flutterTts.setCompletionHandler(() {
      if (mounted) {
        setState(() {
          _speakingMessageIndex = null;
        });
      }
    });
  }

  void _listen() async {
    if (!_isListening) {
      bool available = await _speech.initialize(
        onStatus: (val) => debugPrint('Speech status: $val'),
        onError: (val) => debugPrint('Speech recognition error'),
      );
      if (available) {
        setState(() => _isListening = true);

        // Attempt to find Swahili locale for bilingual dictation if supported, or default
        String? targetLocaleId;
        try {
          var locales = await _speech.locales();
          for (var l in locales) {
            if (l.localeId.startsWith('sw')) {
              targetLocaleId = l.localeId;
              break;
            }
          }
        } catch (e) {
          debugPrint('Speech locales unavailable');
        }

        _speech.listen(
          localeId: targetLocaleId,
          onResult: (val) => setState(() {
            _messageController.text = val.recognizedWords;
          }),
        );
      }
    } else {
      setState(() => _isListening = false);
      _speech.stop();
    }
  }

  void _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _isTyping) return;
    final requestSession = _currentSessionId;
    final requestMessages = _messages;

    setState(() {
      _messages.add({"role": "user", "content": text});
      _isTyping = true;
    });

    _messageController.clear();
    _scrollToBottom();
    _saveCurrentSession();

    final ragService = Provider.of<RagService>(context, listen: false);
    try {
      final response = await ragService.answer(text, _currentModel.id);
      if (!mounted ||
          requestSession != _currentSessionId ||
          !identical(requestMessages, _messages)) {
        return;
      }
      setState(() => _messages.add(response.toMessage()));
      _scrollToBottom();
      _saveCurrentSession();
    } catch (error) {
      if (!mounted ||
          requestSession != _currentSessionId ||
          !identical(requestMessages, _messages)) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            error is RagFailure
                ? error.message
                : 'UniLib could not complete the answer. Please try again.',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _isTyping = false);
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _copyText(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Text copied to clipboard')));
  }

  void _editText(int index, String oldText) {
    if (_isTyping) return;
    setState(() {
      if (index < _messages.length) {
        _messages.removeAt(index);
        // If there is an assistant reply immediately following, remove it too
        if (index < _messages.length &&
            _messages[index]['role'] == 'assistant') {
          _messages.removeAt(index);
        }
      }
    });
    _messageController.text = oldText;
    _focusNode.requestFocus();
  }

  void _speakText(int index, String text) async {
    if (_speakingMessageIndex == index) {
      await _flutterTts.stop();
      setState(() {
        _speakingMessageIndex = null;
      });
    } else {
      await _flutterTts.stop();

      String lowerText = text.toLowerCase();
      final swahiliWords = RegExp(r'\b(habari|mambo|vipi|kwa nini|kwanini|nini|hili|hapa|taarifa|sijapata|kulingana|vitabu|vipande|maelezo|ndiyo|hapana|yake|wao|yote|sana|lakini|katika|kama|yake|yako)\b');
      bool isSwahili = swahiliWords.hasMatch(lowerText);

      if (isSwahili) {
        await _flutterTts.setLanguage("sw-TZ");
        await _flutterTts.setSpeechRate(0.4);
      } else {
        await _flutterTts.setLanguage("en-US");
        await _flutterTts.setSpeechRate(0.5); // Natural English rate
      }

      setState(() {
        _speakingMessageIndex = index;
      });
      await _flutterTts.speak(text);
    }
  }

  void _pickMedia() async {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 16.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Upload Study Media',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                ListTile(
                  leading: const Icon(Icons.photo_library_rounded, color: Color(0xFF1E88E5)),
                  title: const Text('Choose Photo / Image'),
                  onTap: () async {
                    Navigator.pop(context);
                    final picker = ImagePicker();
                    final image = await picker.pickImage(source: ImageSource.gallery);
                    if (image != null && mounted) {
                      _messageController.text += "[Image: ${image.name}] ";
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Image attached: ${image.name}')),
                      );
                    }
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.videocam_rounded, color: Colors.purple),
                  title: const Text('Choose Video File'),
                  onTap: () async {
                    Navigator.pop(context);
                    final picker = ImagePicker();
                    final video = await picker.pickVideo(source: ImageSource.gallery);
                    if (video != null && mounted) {
                      _messageController.text += "[Video: ${video.name}] ";
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Video attached: ${video.name}')),
                      );
                    }
                  },
                ),
                ListTile(
                  leading: const Icon(Icons.camera_alt_rounded, color: Colors.green),
                  title: const Text('Capture from Camera'),
                  onTap: () async {
                    Navigator.pop(context);
                    final picker = ImagePicker();
                    final photo = await picker.pickImage(source: ImageSource.camera);
                    if (photo != null && mounted) {
                      _messageController.text += "[Camera: ${photo.name}] ";
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Photo attached: ${photo.name}')),
                      );
                    }
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showHistoryDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Conversation History'),
          content: SizedBox(
            width: double.maxFinite,
            child: _savedSessions.isEmpty
                ? const Text("No history available.")
                : ListView.builder(
                    shrinkWrap: true,
                    itemCount: _savedSessions.length,
                    itemBuilder: (context, index) {
                      final session = _savedSessions[index];
                      return ListTile(
                        leading: const Icon(Icons.chat_bubble_outline),
                        title: Text(session["title"]),
                        trailing: IconButton(
                          icon: const Icon(
                            Icons.delete_outline,
                            color: Colors.red,
                          ),
                          onPressed: () {
                            _deleteSession(session["id"]);
                            Navigator.pop(context);
                            _showHistoryDialog(); // Refresh dialog
                          },
                        ),
                        onTap: () =>
                            _loadSession(session["id"], session["messages"]),
                      );
                    },
                  ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  void _showAppInfo() {
    showDialog(
      context: context,
      builder: (context) {
        final isDark = Theme.of(context).brightness == Brightness.dark;
        final cardColor = isDark ? const Color(0xFF2C2C2C) : const Color(0xFFF5F7FA);

        Widget buildSpecTile(String title, String value, String description, IconData icon) {
          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: cardColor,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF1E88E5).withValues(alpha: 0.15)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, color: const Color(0xFF1E88E5), size: 22),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        value,
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Color(0xFF1E88E5)),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        description,
                        style: TextStyle(fontSize: 12, color: isDark ? Colors.white70 : Colors.black87, height: 1.3),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        }

        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Column(
            children: const [
              Icon(Icons.school_rounded, size: 58, color: Color(0xFF1E88E5)),
              SizedBox(height: 10),
              Text(
                'UniLib Assistant',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 4),
              Text(
                'Version 1.0.0',
                style: TextStyle(fontSize: 12, color: Colors.grey, fontWeight: FontWeight.w500),
              ),
            ],
          ),
          content: SizedBox(
            width: double.maxFinite,
            height: 450,
            child: ListView(
              shrinkWrap: true,
              children: [
                buildSpecTile(
                  'Languages Used',
                  'Dart & Flutter • Python',
                  'Dart & Flutter power the cross-platform UI and reactive on-device logic. Python was used for OCR extraction, cleaning, and semantic chunking.',
                  Icons.code_rounded,
                ),
                buildSpecTile(
                  'SDK Kits Used',
                  'Flutter SDK 3.x • Android SDK 34 • Google LiteRT',
                  'Built for Android 11+ (API 34) ARM64 with Google LiteRT (TensorFlow Lite / Edge AI SDK) for native neural model acceleration.',
                  Icons.developer_mode_rounded,
                ),
                buildSpecTile(
                  'AI Modules & Open Origin',
                  'Gemma 3 1B-IT & EmbeddingGemma 300M',
                  'Open weights from Google DeepMind / litert-community. Optimized for offline student Q&A with strict factual grounding.',
                  Icons.psychology_rounded,
                ),
                buildSpecTile(
                  'Voice Engine',
                  'Flutter TTS & SpeechToText',
                  'Dual-language voice output (Tanzanian Swahili sw-TZ & US English en-US) and real-time on-device speech dictation.',
                  Icons.record_voice_over_rounded,
                ),
                buildSpecTile(
                  'Runtime File Formats',
                  '.litertlm • .tflite • .model • .jsonl',
                  'Quantized 4-bit Gemma model (.litertlm), vector embedder (.tflite), SentencePiece tokenizer (.model), and SHA-256 verified chunks (.jsonl).',
                  Icons.description_rounded,
                ),
                buildSpecTile(
                  'Vector Database',
                  'SQLite Vector Store Provider',
                  'Stores and indexes 768-dimensional semantic embedding vectors with cosine distance matching directly on device storage.',
                  Icons.storage_rounded,
                ),
                buildSpecTile(
                  'CPU Inference Speed',
                  '~15 - 25 Tokens/Second',
                  'Utilizes multi-threaded CPU inference on ARM64 mobile architecture, answering questions in 1-3 seconds completely offline without cloud servers.',
                  Icons.speed_rounded,
                ),
                buildSpecTile(
                  'Total App Storage',
                  '~1.6 GB Complete Footprint',
                  'Includes App Base (~60MB), Gemma 3 1B model (~1.2GB), EmbeddingGemma (~300MB), and curriculum Vector Database (~50MB).',
                  Icons.memory_rounded,
                ),
                buildSpecTile(
                  'Indexed Content',
                  '451 Verified Curriculum Chunks',
                  'Covers Form One Biology, Chemistry, and Physics textbooks with verified page and PDF references.',
                  Icons.auto_stories_rounded,
                ),
                buildSpecTile(
                  'RAG Strategy Employed',
                  'LiteRT Edge AI RAG + Reciprocal Fusion',
                  'Two-stage retrieval: 768-dim EmbeddingGemma semantic search, Reciprocal-Rank Fusion lexical re-ranking, and grounded generation with textbook citations.',
                  Icons.hub_rounded,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close', style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF1E88E5))),
            ),
          ],
        );
      },
    );
  }

  void _logout() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setBool('isLoggedIn', false);
    if (mounted) {
      Navigator.pop(context);
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const AuthScreen()),
      );
    }
  }

  void _showDrawerMenu(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.add_comment_rounded),
                title: const Text('New Chat'),
                onTap: () {
                  setState(() {
                    _messages.clear();
                    _currentSessionId = DateTime.now().millisecondsSinceEpoch
                        .toString();
                  });
                  Navigator.pop(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.history_rounded),
                title: const Text('Conversation History'),
                onTap: () {
                  Navigator.pop(context);
                  _showHistoryDialog();
                },
              ),
              ListTile(
                leading: const Icon(Icons.school_rounded, color: Color(0xFF1E88E5)),
                title: const Text('Secondary Study Levels'),
                onTap: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => const ClassSelectionScreen(),
                    ),
                  );
                },
              ),
              ListTile(
                leading: const Icon(Icons.info_outline_rounded),
                title: const Text('App Info'),
                onTap: () {
                  Navigator.pop(context);
                  _showAppInfo();
                },
              ),
              const Divider(),
              ListTile(
                leading: const Icon(Icons.logout_rounded, color: Colors.red),
                title: const Text(
                  'Log Out',
                  style: TextStyle(color: Colors.red),
                ),
                onTap: _logout,
              ),
            ],
          ),
        );
      },
    );
  }

  void _showSettings(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setModalState) {
            final themeProvider = Provider.of<ThemeProvider>(context);
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Settings',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    SwitchListTile(
                      title: const Text('Dark Mode'),
                      secondary: const Icon(Icons.dark_mode_rounded),
                      value: themeProvider.isDarkMode,
                      onChanged: (bool value) {
                        themeProvider.toggleTheme(value);
                      },
                    ),
                    const Divider(),
                    ListTile(
                      leading: const Icon(Icons.psychology_rounded),
                      title: const Text('Language Model'),
                      subtitle: Text(_currentModel.name),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      onTap: () {
                        Navigator.pop(context); // close bottom sheet
                        Navigator.pushReplacement(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const ModelSelectionScreen(),
                          ),
                        );
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.record_voice_over_rounded),
                      title: const Text('Voice Model'),
                      subtitle: Text(_currentVoiceModel),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      onTap: () {
                        final newModel =
                            _currentVoiceModel == "Default English (US)"
                            ? "Swahili Premium (TZ)"
                            : "Default English (US)";
                        setModalState(() {
                          _currentVoiceModel = newModel;
                        });
                        setState(() {
                          _currentVoiceModel = newModel;
                        });
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              'Voice model changed to $_currentVoiceModel',
                            ),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    _speech.stop();
    _flutterTts.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    bool canAddMedia = _currentModel.id == 'pro' || _currentModel.id == 'max';
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.more_vert_rounded),
          onPressed: () => _showDrawerMenu(context),
        ),
        title: Column(
          children: [
            const Text(
              'UniLib Assistant',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            Text(
              context.watch<RagService>().status,
              style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF1E88E5),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_rounded),
            onPressed: () => _showSettings(context),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(18),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: const Color(0xFF1E88E5).withValues(alpha: 0.12),
                            ),
                            child: const Icon(
                              Icons.auto_awesome_rounded,
                              size: 64,
                              color: Color(0xFF1E88E5),
                            ),
                          ),
                          const SizedBox(height: 20),
                          Text(
                            _userName,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.w800,
                              color: isDark ? Colors.white : const Color(0xFF1A1A1A),
                              letterSpacing: -0.5,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'How can I help you study today?',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 16,
                              color: isDark ? Colors.white70 : Colors.black54,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16.0),
                    itemCount: _messages.length + (_isTyping ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == _messages.length && _isTyping) {
                        return const Align(
                          alignment: Alignment.centerLeft,
                          child: Padding(
                            padding: EdgeInsets.all(16.0),
                            child: CircularProgressIndicator(),
                          ),
                        );
                      }
                      final msg = _messages[index];
                      final isUser = msg["role"] == "user";
                      return _buildMessageBubble(
                        msg["content"],
                        isUser,
                        index,
                        isDark,
                      );
                    },
                  ),
          ),
          _buildInputArea(canAddMedia, isDark),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(String text, bool isUser, int index, bool isDark) {
    bool isThisSpeaking = _speakingMessageIndex == index;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16.0),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.85,
        ),
        decoration: BoxDecoration(
          color: isUser
              ? const Color(0xFF1E88E5)
              : (isDark ? const Color(0xFF2C2C2C) : Colors.white),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(20),
            topRight: const Radius.circular(20),
            bottomLeft: Radius.circular(isUser ? 20 : 0),
            bottomRight: Radius.circular(isUser ? 0 : 20),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 5,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: isUser
                  ? Text(
                      text,
                      style: const TextStyle(color: Colors.white, fontSize: 16),
                    )
                  : MarkdownBody(
                      data: text,
                      styleSheet: MarkdownStyleSheet(
                        p: TextStyle(
                          color: isDark ? Colors.white : Colors.black87,
                          fontSize: 16,
                          height: 1.4,
                        ),
                      ),
                    ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: isUser
                    ? Colors.blue[600]
                    : (isDark ? const Color(0xFF3C3C3C) : Colors.grey[100]),
                borderRadius: BorderRadius.only(
                  bottomLeft: Radius.circular(isUser ? 20 : 0),
                  bottomRight: Radius.circular(isUser ? 0 : 20),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.end,
                children: isUser
                    ? [
                        IconButton(
                          constraints: const BoxConstraints(),
                          padding: const EdgeInsets.all(4),
                          icon: const Icon(
                            Icons.content_copy_rounded,
                            size: 16,
                            color: Colors.white70,
                          ),
                          onPressed: () => _copyText(text),
                        ),
                        IconButton(
                          constraints: const BoxConstraints(),
                          padding: const EdgeInsets.all(4),
                          icon: const Icon(
                            Icons.edit_rounded,
                            size: 16,
                            color: Colors.white70,
                          ),
                          onPressed: () => _editText(index, text),
                        ),
                      ]
                    : [
                        IconButton(
                          constraints: const BoxConstraints(),
                          padding: const EdgeInsets.all(4),
                          icon: Icon(
                            Icons.content_copy_rounded,
                            size: 18,
                            color: isDark ? Colors.white54 : Colors.black54,
                          ),
                          onPressed: () => _copyText(text),
                        ),
                        IconButton(
                          constraints: const BoxConstraints(),
                          padding: const EdgeInsets.all(4),
                          icon: Icon(
                            isThisSpeaking
                                ? Icons.stop_circle_rounded
                                : Icons.volume_up_rounded,
                            size: 20,
                            color: isThisSpeaking
                                ? Colors.red
                                : (isDark ? Colors.white54 : Colors.black54),
                          ),
                          onPressed: () => _speakText(index, text),
                        ),
                      ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInputArea(bool canAddMedia, bool isDark) {
    return Container(
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
      ),
      child: SafeArea(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF2C2C2C) : Colors.white,
            borderRadius: BorderRadius.circular(30),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 10,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: Row(
            children: [
              if (!_isListening)
                IconButton(
                  icon: const Icon(
                    Icons.add_rounded,
                    color: Color(0xFF1E88E5),
                    size: 28,
                  ),
                  tooltip: 'Upload Media',
                  onPressed: _pickMedia,
                ),
              Expanded(
                child: _isListening
                    ? Container(
                        height: 48,
                        alignment: Alignment.center,
                        child: Row(
                          children: [
                            const Icon(Icons.mic, color: Color(0xFF1E88E5)),
                            const SizedBox(width: 8),
                            const AudioWaveform(),
                            const SizedBox(width: 12),
                            Expanded(
                              flex: 2,
                              child: Text(
                                _messageController.text.isEmpty
                                    ? "Listening..."
                                    : _messageController.text,
                                style: const TextStyle(
                                  color: Color(0xFF1E88E5),
                                  fontWeight: FontWeight.bold,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 8),
                          ],
                        ),
                      )
                    : TextField(
                        controller: _messageController,
                        focusNode: _focusNode,
                        style: TextStyle(
                          color: isDark ? Colors.white : Colors.black87,
                        ),
                        decoration: InputDecoration(
                          hintText: 'Message UniLib...',
                          hintStyle: TextStyle(
                            color: isDark ? Colors.white38 : Colors.grey,
                          ),
                          border: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                          ),
                          fillColor: Colors.transparent,
                        ),
                        onSubmitted: (_) => _sendMessage(),
                      ),
              ),
              IconButton(
                icon: Icon(
                  _isListening ? Icons.mic_rounded : Icons.mic_none_rounded,
                  color: _isListening
                      ? Colors.red
                      : (isDark ? Colors.white54 : Colors.black54),
                  size: 26,
                ),
                onPressed: _listen,
              ),
              if (!_isListening)
                Container(
                  margin: const EdgeInsets.all(4),
                  decoration: const BoxDecoration(
                    color: Color(0xFF1E88E5),
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    icon: const Icon(
                      Icons.arrow_upward_rounded,
                      color: Colors.white,
                    ),
                    onPressed: _isTyping ? null : _sendMessage,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class AudioWaveform extends StatefulWidget {
  const AudioWaveform({super.key});

  @override
  State<AudioWaveform> createState() => _AudioWaveformState();
}

class _AudioWaveformState extends State<AudioWaveform>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(6, (index) {
            final t = (_controller.value + (index * 0.16)) % 1.0;
            final height = 6.0 + (1.0 - (t - 0.5).abs() * 2) * 22.0;
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 2.0),
              width: 3.5,
              height: height,
              decoration: BoxDecoration(
                color: const Color(0xFF1E88E5),
                borderRadius: BorderRadius.circular(3),
              ),
            );
          }),
        );
      },
    );
  }
}
