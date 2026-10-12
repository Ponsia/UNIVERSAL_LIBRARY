"""Validate artifacts and run English lexical retrieval smoke probes. No vector/Gemma evaluation."""
import json,pathlib,hashlib,sqlite3,collections
ROOT=pathlib.Path(__file__).resolve().parent
chunks=[json.loads(l) for l in (ROOT/'Chemistry_RAG_chunks.jsonl').read_text().splitlines()]
audit=json.loads((ROOT/'audit.json').read_text())
assert len(chunks)==audit['chunks']
assert len({c['id'] for c in chunks})==len(chunks)
assert len({c['content_sha256'] for c in chunks})==len(chunks)
for c in chunks:
 assert c['content_sha256']==hashlib.sha256(c['content'].encode()).hexdigest()
 assert c['word_count']==len(c['content'].split())<=230
 assert c['pdf_pages']==sorted(set(c['pdf_pages']))
 assert c['printed_pages']==[p-7 for p in c['pdf_pages']]
 assert not set(c['pdf_pages'])&set(audit['revision_pdf_pages']+[97])
 assert c['embedding_text'].endswith(c['content'])
 assert c['chapter'] and c['topic'] and c['subject']=='Chemistry'
text=(ROOT/'Chemistry_RAG_chunks.txt').read_text()
assert text.count('=== END CHUNK ===')==len(chunks)
assert text.count('=== CHUNK ')==len(chunks)
for term in ['Cobalt: Co.','Copper: Latin name Cuprum; chemical symbol Cu.','Sodium: Latin name Natrium; chemical symbol Na.']:
 assert any(term in c['content'] and c['quality_status']=='visually_verified_transcription' for c in chunks),term
conn=sqlite3.connect(':memory:')
conn.execute('CREATE VIRTUAL TABLE chunks USING fts5(id UNINDEXED, content)')
conn.executemany('INSERT INTO chunks VALUES (?,?)',[(c['id'],c['content']) for c in chunks])
probes=[('Chemistry definition','"composition" AND "structure" AND "matter"',['Chemistry is a branch of science']),('Fire triangle','"fire triangle"',['heat, oxygen and fuel']),('Cobalt symbol','Cobalt',['Cobalt: Co.']),('Solution definition','"solute" AND "solvent"',['A solution is a homogeneous mixture']),('Distillation','"distillation"',['Distillation refers to the process']),('Rusting','"rusting" AND "oxygen"',['iron, oxygen and water'])]
results=[]
for title,query,terms in probes:
 rows=conn.execute('SELECT id,content FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT 5',(query,)).fetchall()
 hits=[i for i,t in rows if all(term.casefold() in t.casefold() for term in terms)]
 assert hits,(title,'Relevant evidence missing from lexical top 5')
 results.append(dict(probe=title,matching_evidence_ids=hits,lexical_top5_ids=[i for i,t in rows]))
report=dict(structural_checks='passed',lexical_smoke_probes='passed',chunks=len(chunks),chapter_counts=dict(collections.Counter(c['chapter'] for c in chunks)),words_including_overlap=sum(c['word_count'] for c in chunks),probes=results,vector_search_tested=False,kiswahili_retrieval_tested=False,gemma_generation_tested=False,latency_measured=False,fully_manually_verified=False)
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
