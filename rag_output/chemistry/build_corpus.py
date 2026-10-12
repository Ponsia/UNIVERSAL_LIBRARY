"""Conservative, auditable OCR cleaning and sentence/section chunking for Chemistry.
No embeddings or inference are performed. Documents are data, not instructions.
"""
import pathlib,re,csv,json,hashlib,statistics,collections,difflib
ROOT=pathlib.Path(__file__).resolve().parent
CACHE=pathlib.Path('/tmp/chemistry_rag_ocr')
SRC=pathlib.Path('/home/egovridc26/Desktop/EGA PTRACTICAL TRAINING - 0046/INDIVIDUAL HACKERTHON/UNILIBRARY/pdf_to_txt/chemistry_form_one.txt')
PDF=SRC.with_name('chemistry_form_one_OCR.pdf')
CHAPTERS=[(8,'Introduction to Chemistry'),(21,'Laboratory techniques and safety'),(66,'Fire, firefighting and flames'),(83,'Matter'),(102,'Elements, compounds and mixtures')]
REVISION=set([19,20,81,82,101])|set(range(62,66))|set(range(130,134))
TOPICS=[(8,'Concept of chemistry'),(9,'Branches of chemistry'),(10,'Relationships of chemistry with other disciplines'),(11,'Applications of chemistry'),(21,'Laboratory safety measures'),(28,'First Aid'),(43,'Basic chemistry laboratory apparatus'),(66,'Fire and the fire triangle'),(67,'Firefighting'),(73,'Flames'),(83,'States of matter'),(87,'Changes of states of matter'),(98,'Physical and chemical changes'),(102,'Elements and chemical symbols'),(108,'Compounds and mixtures'),(117,'Separation of mixtures')]
HEADINGS=['Concept of chemistry','Relationships of chemistry with other related disciplines','Applications of chemistry in the development of a modern society','Agriculture','Medicines','Nutrition and cooking','Manufacturing industries','Transport','Communication','Energy','Laboratory safety measures','Laboratory rules','Safety signs','First Aid','First Aid kit','Basic chemistry laboratory apparatus','Beaker','Measuring cylinder','Pipette','Burette','Volumetric flask','Conical flask','Test tube','Test tube rack','Test tube holder','Thermometer','Bunsen burner','Balance','Filter funnel','Tripod stand','Wire gauze','Evaporating dish','Crucible','Mortar and pestle','Spatula','Fire','Components needed to start fire','Firefighting','Fire extinguishers','Flames','Types of flames','Luminous flame','Non-luminous flame','States of matter','Solid state','Liquid state','Gaseous state','Changes of states of matter','Melting','Freezing','Evaporation','Boiling','Condensation','Sublimation','Physical and chemical changes','Physical changes','Chemical changes','Elements and chemical symbols','Metals','Non-metals','Metalloids','Compounds and mixtures','Compounds','Mixtures','Types of mixtures','Homogeneous mixtures','Heterogeneous mixtures','Solutions','Suspensions','Emulsions','Separation of mixtures','Decantation','Filtration','Evaporation','Crystallisation','Simple distillation','Fractional distillation','Sublimation','Chromatography','Solvent extraction','Winnowing','Sieving','Magnetic separation']
def norm(t):
    t=t.translate(str.maketrans({'‘':"'",'’':"'",'“':'"','”':'"','–':'-','—':'-','\u00ad':''}))
    # Preserve chemical punctuation and meaningful hyphens. Join linewraps only.
    t=re.sub(r'(?<=[a-z])-\n(?=[a-z])','',t)
    t=re.sub(r'\s+',' ',t).strip()
    t=re.sub(r'\b1s\b','is',t)
    for a,b in {'fuminous':'luminous','Bunsen bummer':'Bunsen burner'}.items():t=t.replace(a,b)
    return t

def blocks(n):
    groups=collections.OrderedDict()
    with (CACHE/f'page_{n:03d}.tsv').open() as f:
        for r in csv.DictReader(f,delimiter='\t'):
            if r['level']=='5' and r['text'].strip():groups.setdefault((r['block_num'],r['par_num']),[]).append(r)
    result=[]
    for key,rows in groups.items():
        lines=collections.OrderedDict()
        for r in rows:lines.setdefault(r['line_num'],[]).append(r['text'])
        conf=[float(r['conf']) for r in rows if float(r['conf'])>=0]
        result.append(dict(text=norm('\n'.join(' '.join(v) for v in lines.values())),confidence=round(statistics.mean(conf),2),low_fraction=sum(c<65 for c in conf)/len(conf),block=key[0],page=n))
    return result

def main():
    accepted=[];review=[];seen=set();raw=[]
    verified=[json.loads(line) for line in (ROOT/'verified_transcriptions.jsonl').read_text().splitlines()]
    for n in range(8,134):
        chapter=max((v for v in CHAPTERS if v[0]<=n),key=lambda v:v[0])[1]
        topic=max((v for v in TOPICS if v[0]<=n),key=lambda v:v[0])[1]
        raw.append(dict(pdf_page=n,text=(CACHE/f'page_{n:03d}.txt').read_text()))
        if n==97:
            review.append(dict(pdf_page=n,text=raw[-1]['text'],reasons=['source_pdf_page_is_loading_placeholder_no_lesson_text']))
            continue
        if n in REVISION:
            review.append(dict(pdf_page=n,chapter=chapter,text=raw[-1]['text'],reasons=['revision_page_questions_and_distractors']));continue
        if n in {104,105}:
            for idx,v in enumerate(v for v in verified if v['page']==n):
                accepted.append(dict(v,chapter=chapter,index=idx,block='manual',confidence=None))
            review.append(dict(pdf_page=n,text=raw[-1]['text'],reasons=['raw_ocr_replaced_by_visually_verified_tables']))
            continue
        for idx,b in enumerate(blocks(n)):
            t=b['text'];b.update(chapter=chapter,topic=topic,index=idx)
            if not t:continue
            # Identify headings before checking length; do not embed labels as evidence.
            if len(t.split())<=14:
                matches=difflib.get_close_matches(t.casefold().strip(':.'),[h.casefold() for h in HEADINGS],n=1,cutoff=.9)
                if matches:topic=HEADINGS[[h.casefold() for h in HEADINGS].index(matches[0])];continue
            if re.match(r'^(Activity|Task)\s+\d',t,re.I):
                topic=t.split('Requirements:')[0].split('Procedure')[0].strip()[:160]
                if len(t.split())<10:continue
            b['topic']=topic
            reasons=[]
            if b['confidence']<90 or b['low_fraction']>.10:reasons.append('low_ocr_confidence')
            if re.search(r'(wazaelimu|Student.?s\s*Book|Chemistry for Secondary|READING ONLY)',t,re.I):reasons.append('boilerplate')
            if re.search(r'\b(explain how|explain why|give examples|state whether|which of the following)\b',t,re.I):reasons.append('question_not_answer_evidence')
            if '?' in t or re.match(r'^(Questions|Exercise|Revision|\d+[.)]?\s*(?:Why|How|What|Which|Explain|Describe|Mention|List|Give|State|Identify|Outline))\b',t,re.I):reasons.append('question_not_answer_evidence')
            if re.match(r'^(?:\d+[.)]?\s*)?(Use reliable|Search|Conduct a library|Watch animated|Explain the meaning|Visit a nearby|Write TRUE|Choose|Match|Fill in|Discuss|Prepare a report)\b',t,re.I):reasons.append('learning_task_not_answer_evidence')
            if re.match(r'^(Figure|Fig\.?|Table)\s*\d',t,re.I):reasons.append('caption_or_table_requires_layout_review')
            if 'In this chapter' in t or 'competencies developed' in t:reasons.append('learning_objectives')
            if re.search(r'[|\\{}<>©®]|[a-z][@][a-z]',t):reasons.append('suspicious_ocr_symbols')
            # Formulae, superscripts and ionic charges require source-image verification.
            if re.search(r'\b(?:[A-Z][a-z]?){1,4}[0-9₂₃₄₅₆₇₈₉]+|[→⇌]|\bcm[’\'³²]|\bH[,;_]|\bO[,;_]|[A-Za-z]\^\d',t):reasons.append('formula_or_unit_requires_visual_verification')
            if len(t.split())<3:reasons.append('short_label_or_noise')
            if t in seen:reasons.append('duplicate')
            if reasons:review.append(dict(pdf_page=n,printed_page=n-7,chapter=chapter,topic=topic,text=t,confidence=b['confidence'],reasons=reasons));continue
            seen.add(t);accepted.append(b)
    # Join only adjacent accepted fragments in the same section, never across gaps.
    joined=[]
    for b in accepted:
        prev=joined[-1] if joined else None
        if prev and prev['page']==b['page'] and prev['index']+1==b['index'] and prev['topic']==b['topic'] and not re.search(r'[.!?:]$',prev['text']):
            prev['text']+=' '+b['text'];prev['index']=b['index'];prev['confidence']=min(prev['confidence'],b['confidence'])
        else:joined.append(b.copy())
    clean=[]
    for b in joined:
        t=b['text']
        if not re.search(r'[.!?]$',t):
            ends=list(re.finditer(r'[.!?](?:\s|$)',t));cut=ends[-1].end() if ends else 0
            review.append(dict(pdf_page=b['page'],text=t[cut:].strip(),reasons=['incomplete_sentence_or_table_row']))
            t=t[:cut].strip()
        if len(t.split())<8 or not re.match(r'^(?:[A-Z]|\d+[.)]|\([a-z]\))',t):
            if t:review.append(dict(pdf_page=b['page'],text=t,reasons=['fragment_or_label']))
            continue
        clean.append(dict(b,text=t))
    chunks=[];pending=[];overlap=[]
    def flush():
        nonlocal pending,overlap
        if not pending:return
        allparts=overlap+pending;content='\n\n'.join(b['text'] for b in allparts)
        pages=sorted({p for b in allparts for p in b.get('pages',[b['page']])})
        c=dict(id=f'chemistry_f1_{len(chunks)+1:04d}',source_file=PDF.name,subject='Chemistry',level='Form One',language='en',chapter=pending[0]['chapter'],topic=pending[0]['topic'],pdf_pages=pages,printed_pages=[p-7 for p in pages],word_count=len(content.split()),quality_status='visually_verified_transcription' if all(b.get('verification')=='visually_verified_against_source_pdf' for b in allparts) else 'ocr_screened_not_fully_manually_verified',ocr_mean_confidence_min=min((b['confidence'] for b in allparts if b['confidence'] is not None),default=None),content=content)
        c['embedding_text']=f"Chemistry | Form One | {c['chapter']} | {c['topic']}\n{content}";c['content_sha256']=hashlib.sha256(content.encode()).hexdigest();chunks.append(c)
        tail=re.split(r'(?<=[.!?])\s+',pending[-1]['text'])[-1]
        overlap=[dict(pending[-1],text=tail)] if 8<=len(tail.split())<=30 else []
        pending=[]
    for b in clean:
        parts=[];buf=''
        for sentence in re.split(r'(?<=[.!?])\s+',b['text']):
            if len(sentence.split())>210:
                review.append(dict(pdf_page=b['page'],text=sentence,reasons=['oversized_sentence_requires_review']));continue
            if len((buf+' '+sentence).split())>210:
                parts.append(buf);buf=sentence
            else:buf=(buf+' '+sentence).strip()
        if buf:parts.append(buf)
        for part in parts:
            cur=dict(b,text=part);existing=pending or overlap
            boundary=bool(existing) and (cur['chapter'],cur['topic'])!=(existing[0]['chapter'],existing[0]['topic'])
            if boundary:flush();overlap=[]
            if sum(len(p['text'].split()) for p in pending+overlap)+len(part.split())>230:flush()
            if sum(len(p['text'].split()) for p in overlap)+len(part.split())>230:overlap=[]
            pending.append(cur)
            if sum(len(p['text'].split()) for p in pending)>=170:flush()
    flush()
    def write_jsonl(name,records):
        (ROOT/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in records),encoding='utf-8')
    write_jsonl('Chemistry_RAG_chunks.jsonl',chunks);write_jsonl('Chemistry_review_required.jsonl',review);write_jsonl('Chemistry_source_ocr.jsonl',raw)
    (ROOT/'Chemistry_RAG_chunks.txt').write_text('\n\n'.join(f"=== CHUNK {c['id']} ===\nSource: {c['source_file']}\nSubject: Chemistry | Level: Form One | Language: English\nChapter: {c['chapter']}\nTopic: {c['topic']}\nPDF pages: {', '.join(map(str,c['pdf_pages']))} | Printed pages: {', '.join(map(str,c['printed_pages']))}\nQuality: {c['quality_status']}\nText:\n{c['content']}\n=== END CHUNK ===" for c in chunks)+'\n',encoding='utf-8')
    (ROOT/'Chemistry_cleaned_for_RAG.txt').write_text('\n\n'.join(f"[PDF page: {b['page']} | Printed page: {b['page']-7} | {b['chapter']} | {b['topic']}]\n{b['text']}" for b in clean)+'\n',encoding='utf-8')
    sizes=[c['word_count'] for c in chunks]
    audit=dict(source_file=str(SRC),source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),source_pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),source_words=len(SRC.read_text().split()),ocr_pdf_pages=[8,133],ocr_page_count=len(raw),revision_pdf_pages=sorted(REVISION),chunks=len(chunks),accepted_blocks=len(clean),review_records=len(review),chunk_words_min=min(sizes),chunk_words_median=statistics.median(sizes),chunk_words_max=max(sizes),review_reason_counts=dict(collections.Counter(r for b in review for r in b['reasons'])),coverage='Filtered subset; not a complete verified transcription. Original and all re-OCR pages remain available.',source_loading_placeholder_pdf_pages=[97],visually_verified_table_pdf_pages=[104,105],tokenizer_counts_measured=False,embeddings_generated=False,vector_retrieval_tested=False,gemma_tested=False)
    (ROOT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
