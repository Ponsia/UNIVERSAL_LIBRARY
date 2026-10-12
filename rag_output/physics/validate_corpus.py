"""Structural, formula-preservation and English lexical retrieval checks; no vector/Gemma test."""
import pathlib,json,hashlib,collections,sqlite3,math
ROOT=pathlib.Path(__file__).resolve().parent
chunks=[json.loads(l) for l in (ROOT/'Physics_RAG_chunks.jsonl').read_text().splitlines()]
audit=json.loads((ROOT/'audit.json').read_text())
assert len(chunks)==audit['chunks']
assert len({c['id'] for c in chunks})==len(chunks)
assert len({c['content_sha256'] for c in chunks})==len(chunks)
assert len({c['chapter'] for c in chunks})==9
for c in chunks:
 assert c['word_count']==len(c['content'].split())<=230
 assert c['content_sha256']==hashlib.sha256(c['content'].encode()).hexdigest()
 assert c['pdf_pages']==sorted(set(c['pdf_pages']))
 assert c['printed_pages']==[p-6 for p in c['pdf_pages']]
 assert not set(c['pdf_pages'])&set(audit['revision_pdf_pages'])
 assert c['embedding_text'].endswith(c['content'])
 assert all(7<=p<=228 for p in c['pdf_pages'])
text=(ROOT/'Physics_RAG_chunks.txt').read_text()
assert text.count('=== END CHUNK ===')==len(chunks)
assert text.count('=== CHUNK ')==len(chunks)
verified=[c for c in chunks if c['quality_status']=='visually_verified_transcription']
for equation in ['rho = m / V','P = F / A','P = h * rho * g','a = change in velocity / time taken = (v - u) / t','v = u + a*t','s = u*t + (1/2)*a*t^2','v^2 = u^2 + 2*a*s','W = F*d','KE = (1/2)*m*v^2','PE = m*g*h','P = W / t']:
 assert any(equation in c['content'] for c in verified),equation
assert math.isclose(1.2/(.12*.04*.10),2500)
assert math.isclose(2*10*25,500)
conn=sqlite3.connect(':memory:');conn.execute('CREATE VIRTUAL TABLE chunks USING fts5(id UNINDEXED, content)')
conn.executemany('INSERT INTO chunks VALUES (?,?)',[(c['id'],c['content']) for c in chunks])
probes=[('Physics definition','"matter" AND "energy" AND "interactions"','Physics is the branch of science'),('Density formula','rho AND volume','rho = m / V'),('Relative density','"relative density" AND "ratio"','Relative density, R.D.'),('Hooke law','"elastic" AND "constant" AND "force"','k = F / e'),('Pressure','"normal force" AND "area"','P = F / A'),('Liquid pressure','"rho" AND "liquid"','P = h * rho * g'),('Acceleration','"acceleration" AND "velocity" AND "initial"','(v - u) / t'),('Equations of motion','"uniform" AND "initial" AND "displacement"','v^2 = u^2 + 2*a*s'),('Kinetic energy','"kinetic energy" AND "speed"','KE = (1/2)*m*v^2'),('Power','"power" AND "watts"','P = W / t')]
results=[]
for name,query,evidence in probes:
 rows=conn.execute('SELECT id,content FROM chunks WHERE chunks MATCH ? ORDER BY bm25(chunks) LIMIT 5',(query,)).fetchall()
 matches=[i for i,t in rows if evidence in t]
 assert matches,(name,'No target evidence in lexical top 5')
 results.append(dict(probe=name,matching_evidence_ids=matches,lexical_top5_ids=[i for i,t in rows]))
report=dict(structural_checks='passed',formula_preservation='passed',verified_example_arithmetic='passed',english_lexical_probes='passed',chunks=len(chunks),verified_chunks=len(verified),chapter_counts=dict(collections.Counter(c['chapter'] for c in chunks)),words_including_overlap=sum(c['word_count'] for c in chunks),probes=results,vector_search_tested=False,kiswahili_retrieval_tested=False,gemma_generation_tested=False,latency_measured=False,fully_manually_verified=False)
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
