import os

content = """import 'package:flutter/material.dart';
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
  bool _isSpeaking = false;
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
        loadedSessions.add({
          "id": sessionId,
          "title": "Study Session - " + _formatDate(sessionId),
          "messages": jsonDecode(sessionData)
        });
      }
    }
    setState(() {
      _savedSessions = loadedSessions.reversed.toList();
    });
  }

  String _formatDate(String timestamp) {
    DateTime date = DateTime.fromMillisecondsSinceEpoch(int.parse(timestamp));
    return "${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute}";
  }

  void _saveCurrentSession() async {
    if (_messages.isEmpty) return;
    SharedPreferences prefs = await SharedPreferences.getInstance();
    List<String> sessions = prefs.getStringList('chat_sessions') ?? [];
    if (!sessions.contains(_currentSessionId)) {
      sessions.add(_currentSessionId);
      await prefs.setStringList('chat_sessions', sessions);
    }
    await prefs.setString('chat_session_$_currentSessionId', jsonEncode(_messages));
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
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);
    _flutterTts.setCompletionHandler(() {
      if (mounted) {
        setState(() { _isSpeaking = false; });
      }
    });
  }

  void _listen() async {
    if (!_isListening) {
      bool available = await _speech.initialize(
        onStatus: (val) => print('onStatus: $val'),
        onError: (val) => print('onError: $val'),
      );
      if (available) {
        setState(() => _isListening = true);
        _speech.listen(
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
    if (text.isEmpty) return;

    setState(() {
      _messages.add({"role": "user", "content": text});
      _isTyping = true;
    });

    _messageController.clear();
    _scrollToBottom();
    _saveCurrentSession();

    final ragService = Provider.of<RagService>(context, listen: false);
    final response = await ragService.queryOfflineKnowledgeBase(text, _currentModel.id);

    if (mounted) {
      setState(() {
        _isTyping = false;
        _messages.add({"role": "assistant", "content": response});
      });
      _scrollToBottom();
      _saveCurrentSession();
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
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Text copied to clipboard')),
    );
  }

  void _editText(int index, String oldText) {
    setState(() {
      if (index < _messages.length) {
         _messages.removeAt(index);
         // If there is an assistant reply immediately following, remove it too
         if (index < _messages.length && _messages[index]['role'] == 'assistant') {
             _messages.removeAt(index);
         }
      }
    });
    _messageController.text = oldText;
    _focusNode.requestFocus();
  }

  void _speakText(String text) async {
    if (_isSpeaking) {
      await _flutterTts.stop();
      setState(() { _isSpeaking = false; });
    } else {
      if (_currentVoiceModel == "Swahili Premium (TZ)") {
        await _flutterTts.setLanguage("sw-KE"); // sw-TZ/KE depending on engine
      } else {
        await _flutterTts.setLanguage("en-US");
      }
      setState(() { _isSpeaking = true; });
      await _flutterTts.speak(text);
    }
  }

  void _pickMedia() async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);
    
    if (image != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Media attached: ${image.name}')),
      );
      _messageController.text = "[Image Attached] ";
    }
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
                    icon: const Icon(Icons.delete_outline, color: Colors.red),
                    onPressed: () {
                      _deleteSession(session["id"]);
                      Navigator.pop(context);
                      _showHistoryDialog(); // Refresh dialog
                    },
                  ),
                  onTap: () => _loadSession(session["id"], session["messages"]),
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
      }
    );
  }

  void _showAppInfo() {
    showAboutDialog(
      context: context,
      applicationName: 'UniLib',
      applicationVersion: '1.0.0',
      applicationIcon: const Icon(Icons.school_rounded, size: 48, color: Color(0xFF1E88E5)),
      children: [
        const Text('Universal Library is your ultimate offline AI Study Assistant. It integrates SQLite-vss and small language models to provide curriculum-aligned answers without internet access.'),
      ],
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
                    _currentSessionId = DateTime.now().millisecondsSinceEpoch.toString();
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
                title: const Text('Log Out', style: TextStyle(color: Colors.red)),
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
                    const Text('Settings', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
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
                          MaterialPageRoute(builder: (context) => const ModelSelectionScreen()),
                        );
                      },
                    ),
                    ListTile(
                      leading: const Icon(Icons.record_voice_over_rounded),
                      title: const Text('Voice Model'),
                      subtitle: Text(_currentVoiceModel),
                      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                      onTap: () {
                        setModalState(() {
                          _currentVoiceModel = _currentVoiceModel == "Default English (US)" 
                              ? "Swahili Premium (TZ)" 
                              : "Default English (US)";
                        });
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Voice model changed to $_currentVoiceModel')),
                        );
                      },
                    ),
                  ],
                ),
              ),
            );
          }
        );
      },
    );
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
              'Running ${_currentModel.name} Offline',
              style: TextStyle(fontSize: 12, color: _currentModel.color),
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
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(_currentModel.icon, size: 64, color: _currentModel.color.withOpacity(0.5)),
                        const SizedBox(height: 16),
                        Text(
                          'How can I help you study today, $_userName?',
                          style: TextStyle(fontSize: 18, color: isDark ? Colors.white54 : Colors.black54, fontWeight: FontWeight.w500),
                        ),
                      ],
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
                      return _buildMessageBubble(msg["content"], isUser, index, isDark);
                    },
                  ),
          ),
          _buildInputArea(canAddMedia, isDark),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(String text, bool isUser, int index, bool isDark) {
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
              color: Colors.black.withOpacity(0.05),
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
                        p: TextStyle(color: isDark ? Colors.white : Colors.black87, fontSize: 16, height: 1.4),
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
                          icon: const Icon(Icons.content_copy_rounded, size: 16, color: Colors.white70),
                          onPressed: () => _copyText(text),
                        ),
                        IconButton(
                          constraints: const BoxConstraints(),
                          padding: const EdgeInsets.all(4),
                          icon: const Icon(Icons.edit_rounded, size: 16, color: Colors.white70),
                          onPressed: () => _editText(index, text),
                        ),
                      ]
                    : [
                        IconButton(
                          constraints: const BoxConstraints(),
                          padding: const EdgeInsets.all(4),
                          icon: Icon(Icons.content_copy_rounded, size: 18, color: isDark ? Colors.white54 : Colors.black54),
                          onPressed: () => _copyText(text),
                        ),
                        IconButton(
                          constraints: const BoxConstraints(),
                          padding: const EdgeInsets.all(4),
                          icon: Icon(_isSpeaking ? Icons.stop_circle_rounded : Icons.volume_up_rounded, size: 20, color: _isSpeaking ? Colors.red : (isDark ? Colors.white54 : Colors.black54)),
                          onPressed: () => _speakText(text),
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
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: Row(
            children: [
              if (canAddMedia)
                IconButton(
                  icon: Icon(Icons.add_rounded, color: isDark ? Colors.white54 : Colors.black54, size: 28),
                  onPressed: _pickMedia,
                ),
              Expanded(
                child: TextField(
                  controller: _messageController,
                  focusNode: _focusNode,
                  style: TextStyle(color: isDark ? Colors.white : Colors.black87),
                  decoration: InputDecoration(
                    hintText: 'Message UniLib...',
                    hintStyle: TextStyle(color: isDark ? Colors.white38 : Colors.grey),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                    fillColor: Colors.transparent, // override default theme filled
                  ),
                  onSubmitted: (_) => _sendMessage(),
                ),
              ),
              IconButton(
                icon: Icon(_isListening ? Icons.mic_rounded : Icons.mic_none_rounded, color: _isListening ? Colors.red : (isDark ? Colors.white54 : Colors.black54), size: 26),
                onPressed: _listen,
              ),
              Container(
                margin: const EdgeInsets.all(4),
                decoration: const BoxDecoration(
                  color: Color(0xFF1E88E5),
                  shape: BoxShape.circle,
                ),
                child: IconButton(
                  icon: const Icon(Icons.arrow_upward_rounded, color: Colors.white),
                  onPressed: _sendMessage,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
"""

with open('lib/screens/chat_screen.dart', 'w') as f:
    f.write(content)
