import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_edge_ai/flutter_edge_ai.dart';
import 'package:flutter_edge_ai_embeddings/flutter_edge_ai_embeddings.dart';
import 'package:flutter_edge_ai_litertlm/flutter_edge_ai_litertlm.dart';
import 'package:flutter_edge_ai_rag/flutter_edge_ai_rag.dart';
import 'package:flutter_edge_ai_sqlite/flutter_edge_ai_sqlite.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'rag_types.dart';

class RagFailure implements Exception {
  const RagFailure(this.message);
  final String message;
  @override
  String toString() => message;
}

class RagService extends ChangeNotifier {
  static const embeddingRevision = '29888fcee3216acadc7e844906e5fe0d79a61875';
  static const gemmaRevision = 'a6306a4e292016480083b73b8dc6f3f939ae04c3';
  static const embeddingProfile =
      'embeddinggemma-300m-seq1024-mp-rev-29888fcee321-retrieval-prefix-meanpool-l2-v1';
  static const embeddingFile = 'tie_embeddinggemma_29888fcee321_seq1024.tflite';
  static const tokenizerFile =
      'tie_embeddinggemma_29888fcee321_sentencepiece.model';
  static const gemmaFile = 'Gemma3-1B-IT_multi-prefill-seq_q4_ekv4096.litertlm';
  static const gemmaUrl =
      'https://huggingface.co/litert-community/Gemma3-1B-IT/resolve/$gemmaRevision/$gemmaFile';
  static const embeddingBase =
      'https://huggingface.co/litert-community/embeddinggemma-300m/resolve/$embeddingRevision';

  // Starting operating point; calibrate with bilingual retrieval evaluation.
  static const minimumSimilarity = 0.15;
  static const contextTokens = 4096;
  static const outputTokens = 512;
  static const promptTokens = 2800; // Leaves space for chat framing + answer.

  RagIndex? _index;
  InferenceModel? _model;
  EmbeddingModel? _embeddingModel;
  EmbeddingTokenizer? _tokenizer;
  final Map<String, TieChunk> _chunks = {};
  Future<void>? _initialization;
  Completer<void>? _operationDone;
  String _corpusHash = '';
  bool _ready = false;
  bool _busy = false;
  bool _disposed = false;
  bool get isReady => _ready;
  bool get isBusy => _busy;
  int get chunkCount => _chunks.length;
  String status = 'Reading library textbooks...';
  double progress = 0;

  void _update(String message, {double? fraction}) {
    status = message;
    if (fraction != null) progress = fraction.clamp(0, 1);
    if (!_disposed) notifyListeners();
  }

  Future<void> initKnowledgeBase() => _initialization ??= _initialize();

  Future<void> _initialize() async {
    try {
      final raw = await Future.wait(tieCorpusAssets.map(rootBundle.loadString));
      _corpusHash = sha256.convert(utf8.encode(raw.join('\n'))).toString();
      _chunks.clear();
      for (final chunk in raw.expand(TieChunk.parse)) {
        if (_chunks.containsKey(chunk.id)) {
          throw FormatException('Duplicate corpus ID: ${chunk.id}');
        }
        _chunks[chunk.id] = chunk;
      }
      if (kIsWeb || !Platform.isAndroid) {
        _update('Offline UniLib requires an Android 11+ device with ARM64.');
        return;
      }
      await FlutterEdgeAi.initialize(
        inferenceEngines: const [LiteRtLmEngine()],
        embeddingBackends: const [LiteRtEmbeddingBackend()],
        embeddingTokenizers: const [GemmaEmbeddingTokenizers()],
      );
      if (await _hasExpectedModels()) {
        await _openIndex();
        final stats = await _index!.stats();
        final prefs = await SharedPreferences.getInstance();
        final journal = prefs.getStringList(_journalKey) ?? [];
        _ready =
            stats.documentCount == _chunks.length &&
            journal.toSet().containsAll(_chunks.keys) &&
            journal.length == _chunks.length;
      }
      _update(
        _ready
            ? 'Gemma 3 1B • Offline • ${_chunks.length} chunks'
            : 'Download models and prepare database to start.',
      );
    } catch (_) {
      _update(
        'UniLib preparation incomplete. Open settings and try again.',
      );
      _initialization = null;
      rethrow;
    }
  }

  String get _journalKey => 'tie_index_v1_${embeddingProfile}_$_corpusHash';

  Future<bool> _hasExpectedModels() async {
    final generation = FlutterEdgeAi.activeModelSpec;
    final embedding = FlutterEdgeAi.activeEmbedderSpec;
    final prefs = await SharedPreferences.getInstance();
    if (generation == null ||
        embedding == null ||
        generation.files.first.filename != gemmaFile ||
        generation.modelType != ModelType.gemmaIt ||
        generation.fileType != ModelFileType.litertlm ||
        prefs.getString('tie_gemma_revision') != gemmaRevision ||
        embedding.files[0].filename != embeddingFile ||
        embedding.files[1].filename != tokenizerFile) {
      return false;
    }
    for (final file in [...generation.files, ...embedding.files]) {
      if (!await File(
        await FlutterEdgeAi.getModelPath(file.filename),
      ).exists()) {
        return false;
      }
    }
    return true;
  }

  Future<void> _openIndex() async {
    if (_index != null) return;
    final directory = await getApplicationDocumentsDirectory();
    _index =
        await FlutterEdgeAiRag(
          providers: const [SqliteVectorStoreProvider()],
        ).open(
          spec: VectorStoreSpec(
            providerId: 'sqlite',
            location: p.join(
              directory.path,
              'tie_${embeddingProfile}_${_corpusHash.substring(0, 16)}.db',
            ),
          ),
          embeddingProfile: EmbeddingProfile(
            id: embeddingProfile,
            dimension: 768,
          ),
        );
  }

  Future<void> _loadEmbedder() async {
    _embeddingModel ??= await FlutterEdgeAi.getActiveEmbedder(
      preferredBackend: PreferredBackend.cpu,
    );
    if (await _embeddingModel!.getDimension() != 768) {
      throw const RagFailure('Embedding model haifanani na database ya TIE.');
    }
    _tokenizer ??= await const GemmaEmbeddingTokenizers().factory(
      await FlutterEdgeAi.getModelPath(tokenizerFile),
    );
  }

  Future<List<double>> _embed(String text, TaskType task) async {
    await _loadEmbedder();
    if (_tokenizer!.encode(task.prefix, text).ids.length > 1024) {
      throw const RagFailure(
        'Maandishi ni marefu mno kwa model. Fupisha swali; ikiwa tatizo '
        'linatokea wakati wa maandalizi, data ya vitabu inahitaji kusasishwa.',
      );
    }
    final vector = await _embeddingModel!.generateEmbedding(
      text,
      taskType: task,
    );
    if (vector.length != 768 ||
        vector.any((v) => !v.isFinite) ||
        !vector.any((v) => v != 0)) {
      throw const RagFailure('Embedding model haijatoa vector sahihi.');
    }
    return vector;
  }

  /// The token is used for the install only; UniLib does not save it in prefs.
  /// Repeated setup resumes the completed corpus and reuses downloaded models.
  Future<void> prepareOffline({String token = ''}) async {
    if (_disposed) throw const RagFailure('UniLib imefungwa.');
    if (_busy) throw const RagFailure('UniLib inaendelea na kazi nyingine.');
    _busy = true;
    _operationDone = Completer<void>();
    _ready = false;
    _update('Preparing UniLib...', fraction: 0);
    try {
      await initKnowledgeBase();
      if (kIsWeb || !Platform.isAndroid) {
        throw const RagFailure(
          'Use Android 11+ with ARM64 for offline UniLib.',
        );
      }
      final accessToken = token.trim().isEmpty ? null : token.trim();
      _update('Downloading Gemma 3 1B...');
      await FlutterEdgeAi.installModel(
        modelType: ModelType.gemmaIt,
        fileType: ModelFileType.litertlm,
      ).fromNetwork(gemmaUrl, token: accessToken).withProgress((v) {
        _update('Downloading Gemma 3 1B...', fraction: v / 100);
      }).install();
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('tie_gemma_revision', gemmaRevision);
      _update('Downloading EmbeddingGemma and tokenizer...', fraction: 0);
      await FlutterEdgeAi.installEmbedder()
          .modelFromNetwork(
            '$embeddingBase/embeddinggemma-300M_seq1024_mixed-precision.tflite',
            token: accessToken,
            filename: embeddingFile,
          )
          .tokenizerFromNetwork(
            '$embeddingBase/sentencepiece.model',
            token: accessToken,
            filename: tokenizerFile,
          )
          .withModelProgress(
            (v) => _update('Downloading EmbeddingGemma...', fraction: v / 100),
          )
          .withTokenizerProgress(
            (v) => _update('Downloading tokenizer...', fraction: v / 100),
          )
          .install();
      if (!await _hasExpectedModels()) {
        throw const RagFailure('Model zilizohifadhiwa hazilingani na UniLib.');
      }
      await _openIndex();
      final completed = (prefs.getStringList(_journalKey) ?? []).toSet();
      // A lost/mismatched journal must not allow a partially indexed corpus to
      // masquerade as ready. This clears only this versioned TIE index.
      if (completed.every(_chunks.containsKey) &&
          (await _index!.stats()).documentCount > completed.length) {
        // A process kill can leave a durable vector just before its checkpoint.
        // Remove only uncheckpointed IDs so completed work remains usable.
        for (final id in _chunks.keys.where((id) => !completed.contains(id))) {
          await _index!.remove(id: id);
        }
      }
      if ((await _index!.stats()).documentCount != completed.length ||
          !completed.every(_chunks.containsKey)) {
        await _index!.clear();
        completed.clear();
        await prefs.setStringList(_journalKey, []);
      }
      for (final chunk in _chunks.values) {
        if (completed.contains(chunk.id)) continue;
        _update(
          'Indexing textbooks into vector database: '
          '${completed.length}/${_chunks.length}',
          fraction: completed.length / _chunks.length,
        );
        final vector = await _embed(
          chunk.embeddingText,
          TaskType.retrievalDocument,
        );
        await _index!.addVector(
          id: chunk.id,
          content: chunk.embeddingText,
          embedding: vector,
          metadata: jsonEncode(chunk.data),
        );
        completed.add(chunk.id);
        // The vector write is durable before the checkpoint. Interrupted writes
        // are safely replaced (same ID) if they were not checkpointed.
        await prefs.setStringList(_journalKey, completed.toList());
      }
      await _index!.flush();
      if ((await _index!.stats()).documentCount != _chunks.length) {
        throw const RagFailure(
          'Vector database indexing incomplete. Please try again.',
        );
      }
      _update('Loading Gemma 3 1B...');
      _model ??= await FlutterEdgeAi.getActiveModel(
        maxTokens: contextTokens,
        preferredBackend: PreferredBackend.cpu,
        supportImage: false,
        supportAudio: false,
      );
      await prefs.setString('downloaded_model', 'lite');
      await prefs.remove(
        'model_path',
      ); // Removes the old Qwen-as-Gemma selection.
      _ready = true;
      _update(
        'Gemma 3 1B • Offline • ${_chunks.length} chunks',
        fraction: 1,
      );
    } catch (error) {
      _ready = false;
      _update(
        'Setup failed. Please check internet connection, available storage, and try again.',
      );
      // Download errors may contain authenticated URLs. Do not expose them.
      if (error is RagFailure) rethrow;
      throw const RagFailure(
        'Maandalizi yameshindikana. Kubali leseni za model '
        'kwenye Hugging Face na tumia token yenye read access. '
        'Hakiki pia Android 11+, ARM64 na nafasi ya kuhifadhi.',
      );
    } finally {
      _busy = false;
      _operationDone?.complete();
      if (!_disposed) notifyListeners();
    }
  }

  Future<RagAnswer> answer(String question, String modelId) async {
    if (_disposed) throw const RagFailure('UniLib imefungwa.');
    await initKnowledgeBase();
    if (!_ready || _index == null) {
      throw const RagFailure(
        'UniLib haijawa tayari. Fungua maandalizi ya model kwanza.',
      );
    }
    if (modelId != 'lite') {
      throw const RagFailure('Chagua Gemma 3 1B kwa UniLib.');
    }
    if (_busy) throw const RagFailure('Subiri jibu la swali lililotangulia.');
    final query = question.trim();
    if (query.isEmpty) throw const RagFailure('Andika swali kwanza.');
    _busy = true;
    _operationDone = Completer<void>();
    final lowerQuery = query.toLowerCase();
    bool isSwahili = lowerQuery.contains("mambo") || lowerQuery.contains("habari") || lowerQuery.contains("vipi") || lowerQuery.contains("sasa");
    bool isEnglish = lowerQuery.contains("hello") || lowerQuery.contains("hi") || lowerQuery.contains("how are you");
    if ((isSwahili || isEnglish) && query.split(' ').length <= 4) {
       _busy = false;
       _operationDone?.complete();
       if (isSwahili && isEnglish) {
          return RagAnswer(text: "Hello! Mambo vipi? I am UniLib AI, msaidizi wako wa masomo. Nimejifunza Chemistry, Biology, and Physics. Feel free to ask any question!", sources: [], retrievalMilliseconds: 0, generationMilliseconds: 0);
       } else if (isSwahili) {
          return RagAnswer(text: "Habari! Mimi ni UniLib AI, msaidizi wako wa masomo. Nimejifunza vitabu vya Chemistry, Biology na Physics. Niulize swali lolote la kitaaluma!", sources: [], retrievalMilliseconds: 0, generationMilliseconds: 0);
       } else if (isEnglish) {
          return RagAnswer(text: "Hello! I am UniLib AI, your study assistant. I have learned textbooks for Chemistry, Biology, and Physics. Ask me any academic question!", sources: [], retrievalMilliseconds: 0, generationMilliseconds: 0);
       }
    }

    _update('Searching retrieved textbooks...');
    InferenceModelSession? session;
    try {
      final retrieval = Stopwatch()..start();
      final vector = await _embed(query, TaskType.retrievalQuery);
      final matches = await _index!.searchVector(
        embedding: vector,
        topK: 12,
        threshold: minimumSimilarity,
      );
      final ranked = rankTieHits(
        query,
        matches.map((m) => TieHit(_chunks[m.id]!, m.similarity)).toList(),
      );
      retrieval.stop();
      if (ranked.isEmpty) {
        return RagAnswer(
          text: unavailableAnswer,
          sources: const [],
          retrievalMilliseconds: retrieval.elapsedMilliseconds,
          generationMilliseconds: 0,
        );
      }
      _update('Gemma is generating answer from textbooks...');
      final generation = Stopwatch()..start();
      _model ??= await FlutterEdgeAi.getActiveModel(
        maxTokens: contextTokens,
        preferredBackend: PreferredBackend.cpu,
        supportImage: false,
        supportAudio: false,
      );
      session = await _model!.createSession(
        temperature: 0.1,
        topK: 1,
        maxOutputTokens: outputTokens,
        enableVisionModality: false,
        enableAudioModality: false,
      );
      final selected = <TieChunk>[];
      // Runtime token-count budget, independently of the embedding tokenizer.
      // LiteRT uses a conservative estimate if native token counting fails.
      for (final hit in ranked) {
        if (selected.length == 4) break;
        if (await session.sizeInTokens(
              buildTiePrompt(query, [...selected, hit.chunk]),
            ) <=
            promptTokens) {
          selected.add(hit.chunk);
        }
      }
      if (selected.isEmpty) {
        throw const RagFailure(
          'Swali ni refu mno kwa context ya Gemma. Lifupishe.',
        );
      }
      await session.addQueryChunk(
        Message.text(text: buildTiePrompt(query, selected), isUser: true),
      );
      final generated = await session.getResponse();
      generation.stop();
      return RagAnswer(
        text: formatGroundedAnswer(generated, selected),
        sources: selected,
        retrievalMilliseconds: retrieval.elapsedMilliseconds,
        generationMilliseconds: generation.elapsedMilliseconds,
      );
    } catch (error) {
      if (error is RagFailure) rethrow;
      throw const RagFailure(
        'UniLib imeshindwa kukamilisha jibu. Jaribu tena; '
        'tatizo likiendelea, fungua maandalizi ya model.',
      );
    } finally {
      try {
        await session?.close();
      } catch (_) {
        // Preserve the answer/error while still releasing the request gate.
      } finally {
        _busy = false;
        _operationDone?.complete();
        _update('Gemma 3 1B • TIE offline • ${_chunks.length} chunks');
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    unawaited(_closeResources());
    super.dispose();
  }

  Future<void> _closeResources() async {
    await _operationDone?.future;
    try {
      await _index?.dispose();
      await _model?.close();
      await _embeddingModel?.close();
    } catch (_) {
      debugPrint('UniLib resource cleanup did not finish.');
    }
  }
}
