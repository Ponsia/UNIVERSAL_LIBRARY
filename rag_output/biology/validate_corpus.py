"""Structural and evidence-presence checks; not a vector/Gemma benchmark."""
import json,pathlib,hashlib,collections,re
ROOT=pathlib.Path(__file__).resolve().parent
chunks=[json.loads(x) for x in (ROOT/'Biology_RAG_chunks.jsonl').read_text().splitlines()]
assert len({c['id'] for c in chunks})==len(chunks)
assert len({c['content_sha256'] for c in chunks})==len(chunks)
for c in chunks:
    assert c['content_sha256']==hashlib.sha256(c['content'].encode()).hexdigest()
    assert c['word_count']==len(c['content'].split())<=230
    assert c['pdf_pages']==sorted(set(c['pdf_pages']))
    assert all(7<=p<=147 for p in c['pdf_pages'])
    assert c['printed_pages']==[p-6 for p in c['pdf_pages']]
    assert c['content'].strip() and c['embedding_text'].endswith(c['content'])
    assert not any(p in c['pdf_pages'] for p in [14,15,39,40,41,56,57,68,69,117,118,119,141,142,143])
    assert not re.search(r'CAwitterenine|SIZENRIADS|Microelements are needed by plants in large quantities',c['content'])
text=(ROOT/'Biology_RAG_chunks.txt').read_text()
assert text.count('=== END CHUNK ===')==len(chunks)
probes={
 'Biology definition':['Biology is a branch of science','study of life'],
 'Branches table':['Anatomy: Body structures','Cytology: Structure and functions','Taxonomy: Classification'],
 'Mitochondria':['mitochondria','energy'],
 'Classification':['classification','similarities and differences'],
 'Photosynthesis':['Photosynthesis is the process','water and carbon dioxide'],
 'Xylem and phloem':['Xylem transports','phloem transports'],
}
results=[]
for name,terms in probes.items():
 ids=[c['id'] for c in chunks if all(t.casefold() in c['content'].casefold() for t in terms)]
 assert ids,(name,'Missing evidence')
 results.append(dict(probe=name,evidence_chunk_ids=ids))
report=dict(structural_checks='passed',chunks=len(chunks),chapter_counts=dict(collections.Counter(c['chapter'] for c in chunks)),words_including_overlap=sum(c['word_count'] for c in chunks),evidence_presence_probes=results,vector_search_tested=False,gemma_generation_tested=False,fully_manually_verified=False)
(ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
