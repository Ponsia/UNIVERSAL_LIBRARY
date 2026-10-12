import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_edge_ai_rag/flutter_edge_ai_rag.dart';
import 'package:flutter_edge_ai_sqlite/flutter_edge_ai_sqlite.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() {
    // flutter_tester does not add bundled Native Assets to dlopen's Linux
    // search path. Use the provider's documented host-test override only.
    if (Platform.isLinux) {
      final library = File('build/native_assets/linux/libvec0.so');
      expect(
        library.existsSync(),
        isTrue,
        reason: 'Run flutter test so the sqlite-vec native asset is built.',
      );
      SqliteVectorStore.debugOverrideDylibPath = library.absolute.path;
    }
  });
  test(
    'Real sqlite-vec retrieves, persists, upserts and rejects a wrong profile',
    () async {
      final directory = await Directory.systemTemp.createTemp(
        'unilib-vector-test-',
      );
      final service = FlutterEdgeAiRag(
        providers: const [SqliteVectorStoreProvider()],
      );
      final spec = VectorStoreSpec(
        providerId: 'sqlite',
        location: '${directory.path}/tie.db',
      );
      final profile = EmbeddingProfile(
        id: 'synthetic-test-space-v1',
        dimension: 3,
      );
      RagIndex? index;
      try {
        index = await service.open(spec: spec, embeddingProfile: profile);
        await index.addVector(
          id: 'force',
          content: 'Force',
          embedding: [1, 0, 0],
          metadata: '{"pdf_pages":[10]}',
        );
        await index.addVector(
          id: 'heat',
          content: 'Heat',
          embedding: [0, 1, 0],
        );
        await index.addVector(
          id: 'force',
          content: 'Force updated',
          embedding: [1, 0, 0],
          metadata: '{"pdf_pages":[10]}',
        );
        expect((await index.stats()).documentCount, 2);
        final hits = await index.searchVector(
          embedding: [1, 0.05, 0],
          topK: 2,
          threshold: 0.35,
        );
        expect(hits.map((h) => h.id), ['force']);
        expect(hits.first.similarity, greaterThan(0.99));
        expect(hits.first.content, 'Force updated');
        expect(hits.first.metadata, '{"pdf_pages":[10]}');
        await index.dispose();
        index = null;
        index = await service.open(spec: spec, embeddingProfile: profile);
        expect((await index.stats()).documentCount, 2);
        expect(
          (await index.searchVector(embedding: [0, 1, 0], topK: 1)).first.id,
          'heat',
        );
        expect(
          () => index!.searchVector(embedding: [1, 0]),
          throwsArgumentError,
        );
        await index.dispose();
        index = null;
        await expectLater(
          service.open(
            spec: spec,
            embeddingProfile: EmbeddingProfile(
              id: 'different-model',
              dimension: 3,
            ),
          ),
          throwsStateError,
        );
      } finally {
        await index?.dispose();
        await directory.delete(recursive: true);
      }
    },
  );
}
