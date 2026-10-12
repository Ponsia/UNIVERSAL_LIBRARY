import re

with open('lib/screens/chat_screen.dart', 'r') as f:
    content = f.read()

# Add imports
imports = """import 'package:flutter/material.dart';
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
"""

content = re.sub(r"import 'package:flutter/material\.dart';.*import 'package:unilib/screens/model_selection_screen\.dart';", imports, content, flags=re.DOTALL)

# Add variables
vars = """  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();
  final FlutterTts _flutterTts = FlutterTts();
  late stt.SpeechToText _speech;
  bool _isListening = false;
  bool _isSpeaking = false;
  
  List<Map<String, dynamic>> _messages = [];
  List<Map<String, dynamic>> _savedSessions = [];
  String _currentSessionId = DateTime.now().millisecondsSinceEpoch.toString();
  String _userName = "Student";
"""

content = re.sub(r"  final TextEditingController _messageController = TextEditingController\(\);.*?String _currentVoiceModel = \"Default English \(US\)\";", vars + "\n  bool _isTyping = false;\n  late AIModelInfo _currentModel;\n  String _currentVoiceModel = \"Default English (US)\";", content, flags=re.DOTALL)

# Modify initState
init_state = """  @override
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
"""

content = re.sub(r"  @override\n  void initState\(\) \{.*?  void _initTts\(\) async \{", init_state + "\n  void _initTts() async {", content, flags=re.DOTALL)

# Modify TTS & Send Message
tts_send = """  void _initTts() async {
    await _flutterTts.setLanguage("en-US");
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);
    _flutterTts.setCompletionHandler(() {
      if (mounted) setState(() { _isSpeaking = false; });
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
  }"""

content = re.sub(r"  void _initTts\(\) async \{.*?    \}\n  \}", tts_send, content, flags=re.DOTALL)

# Modify Edit & Speak
edit_speak = """  void _editText(int index, String oldText) {
    setState(() {
      _messages.removeAt(index);
      if (index < _messages.length && _messages[index]['role'] == 'assistant') {
        _messages.removeAt(index); // Remove assistant's reply too
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
  }"""

content = re.sub(r"  void _editText.*?  \}", edit_speak, content, flags=re.DOTALL)

# Modify History Dialog
hist_dialog = """  void _showHistoryDialog() {
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
  }"""

content = re.sub(r"  void _showHistoryDialog\(\) \{.*?          \],\n        \);\n      \}\n    \);\n  \}", hist_dialog, content, flags=re.DOTALL)


# Modify Greeting
greet = """Text(
                          'How can I help you study today, $_userName?',"""
content = re.sub(r"Text\(\n\s*'How can I help you study today\?',", greet, content)

# Modify New Chat logic
new_chat = """              ListTile(
                leading: const Icon(Icons.add_comment_rounded),
                title: const Text('New Chat'),
                onTap: () {
                  setState(() {
                    _messages.clear();
                    _currentSessionId = DateTime.now().millisecondsSinceEpoch.toString();
                  });
                  Navigator.pop(context);
                },
              ),"""
content = re.sub(r"              ListTile\(\n\s*leading: const Icon\(Icons\.add_comment_rounded\),\n\s*title: const Text\('New Chat'\),\n\s*onTap: \(\) \{\n\s*setState\(\(\) \{\n\s*_messages\.clear\(\);\n\s*\}\);\n\s*Navigator\.pop\(context\);\n\s*\},\n\s*\),", new_chat, content)

# Modify Focus Node & STT Icon
stt_btn = """              IconButton(
                icon: Icon(_isListening ? Icons.mic_rounded : Icons.mic_none_rounded, color: _isListening ? Colors.red : (isDark ? Colors.white54 : Colors.black54), size: 26),
                onPressed: _listen,
              ),"""
content = re.sub(r"              IconButton\(\n\s*icon: Icon\(Icons\.mic_none_rounded, color: isDark \? Colors\.white54 : Colors\.black54, size: 26\),\n\s*onPressed: \(\) \{\n\s*ScaffoldMessenger\.of\(context\)\.showSnackBar\(\n\s*const SnackBar\(content: Text\('Listening\.\.\. \(Simulated\)'\)\),\n\s*\);\n\s*\},\n\s*\),", stt_btn, content)

focus = """                  controller: _messageController,
                  focusNode: _focusNode,"""
content = re.sub(r"                  controller: _messageController,", focus, content)

tts_icon_user = """Icon(Icons.volume_up_rounded, size: 20, color: isDark ? Colors.white54 : Colors.black54)"""
tts_icon_agent = """Icon(_isSpeaking ? Icons.stop_circle_rounded : Icons.volume_up_rounded, size: 20, color: _isSpeaking ? Colors.red : (isDark ? Colors.white54 : Colors.black54))"""
content = re.sub(r"Icon\(Icons\.volume_up_rounded, size: 20, color: isDark \? Colors\.white54 : Colors\.black54\)", tts_icon_agent, content)

with open('lib/screens/chat_screen.dart', 'w') as f:
    f.write(content)
