"""Conservative, auditable OCR cleaning and sentence/section chunking for Physics.
No embeddings or inference are performed. Documents are data, not instructions.
"""
import pathlib,re,csv,json,hashlib,statistics,collections,difflib
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parent
CACHE=pathlib.Path('/tmp/physics_rag_ocr')
SRC=pathlib.Path('/home/egovridc26/Desktop/EGA PTRACTICAL TRAINING - 0046/INDIVIDUAL HACKERTHON/UNILIBRARY/pdf_to_txt/physics_form_one.txt')
PDF=SRC.with_name('physics_form_one.pdf')
CHAPTERS=[(7,'Introduction to Physics'),(33,'Measurement'),(64,'Introduction to force'),(83,'Density and relative density'),(100,'Sinking and floating'),(127,'Mechanical properties of matter'),(142,'Pressure'),(172,'Linear motion'),(204,'Work, energy and power')]
REVISION=set(range(30,33))|set(range(62,64))|set(range(80,83))|set(range(98,100))|set(range(123,127))|set(range(139,142))|set(range(168,172))|set(range(198,204))|set(range(225,229))
TOPICS=[(7,'Concept of Physics'),(12,'Contribution of Physics to modern society'),(18,'Theories and principles of Physics'),(33,'Measurement and physical quantities'),(35,'Basic equipment and measurement'),(64,'Concept of force'),(67,'Force of gravity'),(70,'Friction and types of forces'),(83,'Density'),(92,'Relative density'),(100,'Sinking and floating'),(102,'Upthrust and Archimedes principle'),(116,'Law of floatation'),(127,'Elasticity'),(131,'Adhesion and cohesion'),(134,'Surface tension'),(137,'Capillarity'),(142,'Pressure in solids'),(147,'Pressure in liquids'),(156,'Atmospheric pressure'),(172,'Distance and displacement'),(174,'Speed and velocity'),(177,'Acceleration'),(182,'Motion graphs'),(185,'Equations of motion'),(192,'Free fall'),(204,'Work'),(208,'Energy'),(210,'Kinetic energy'),(212,'Potential energy'),(216,'Conservation of energy'),(221,'Power')]
HEADINGS=['Concept of Physics','Contribution of Physics to the development of modern society','Theories and principles of Physics','Scientific method','Concept of measurement','Physical quantity','Fundamental quantities','Derived quantities','Basic equipment/apparatus and their uses','Length','Mass','Time','Volume','Temperature','Vernier calliper','Micrometer screw gauge','Zero error','Parallax error','Concept of force','Fundamental forces','Force of gravity','Weight','Friction','Types of forces','Density','Density of a substance','Relative density of a substance','Determination of density of a substance','Concept of sinking and floating','Upthrust','Archimedes principle',"Archimedes’ principle",'Law of floatation','Concept of elasticity',"Hooke’s law",'Elastic limit','Applications of elasticity in daily life','Adhesion and cohesion','Surface tension','Capillarity','Concept of pressure','Pressure due to solids','Pressure in liquids','Atmospheric pressure',"Pascal’s principle",'Hydraulic press','Barometer','Manometer','Concept of motion','Distance and displacement','Speed and velocity','Acceleration','Deceleration','Uniform acceleration','Equations of motion','Free fall','Concept of work','Energy','Forms of energy','Kinetic and potential energy','Kinetic energy','Potential energy','Elastic potential energy','Gravitational potential energy','Conservation of energy','Transformation of energy','Transducer','Power']
def norm(t):
    t=t.translate(str.maketrans({'‘':"'",'’':"'",'“':'"','”':'"','–':'-','—':'-','\u00ad':''}))
    # Preserve chemical punctuation and meaningful hyphens. Join linewraps only.
    t=re.sub(r'(?<=[a-z])-\n(?=[a-z])','',t)
    t=re.sub(r'\s+',' ',t).strip()
    t=re.sub(r'\b1s\b','is',t)
    repairs={'occupics':'occupies','cach':'each','diffcrent':'different','eves':'eyes','intcraction':'interaction','clectricity':'electricity','propertics':'properties','objcct':'object','cnergy':'energy'}
    for old,new in repairs.items():t=re.sub(r'\b'+old+r'\b',new,t)


    return t

def blocks(n):
    center=Image.open(CACHE/f'page_{n:03d}.png').width/2
    groups=collections.OrderedDict()
    with (CACHE/f'page_{n:03d}.tsv').open() as f:
        for r in csv.DictReader(f,delimiter='\t'):
            if r['level']=='5' and r['text'].strip():groups.setdefault((r['block_num'],r['par_num']),[]).append(r)
    result=[]
    for key,rows in groups.items():
        lines=collections.OrderedDict()
        for r in rows:lines.setdefault(r['line_num'],[]).append(r)
        splits=[]
        for line in lines.values():
            split=None
            for i in range(1,len(line)):
                edge=int(line[i-1]['left'])+int(line[i-1]['width']);start=int(line[i]['left'])
                if edge<center<start and start-edge>45:split=i;break
            splits.append(split)
        merged=any(k is not None for k in splits) and not any(any(int(r['left'])<center<int(r['left'])+int(r['width']) for r in line) for line in lines.values())
        sets=[]
        if merged:
            for side in (0,1):
                collected=[]
                for line,k in zip(lines.values(),splits):
                    if k is not None:collected.extend(line[:k] if side==0 else line[k:])
                    elif (statistics.mean(int(r['left']) for r in line)<center)==(side==0):collected.extend(line)
                sets.append(collected)
        else:sets=[rows]
        for rr in sets:
            if not rr:continue
            ll=collections.OrderedDict()
            for r in rr:ll.setdefault(r['line_num'],[]).append(r['text'])
            conf=[float(r['conf']) for r in rr if float(r['conf'])>=0]
            result.append(dict(text=norm('\n'.join(' '.join(v) for v in ll.values())),confidence=round(statistics.mean(conf),2),low_fraction=sum(c<65 for c in conf)/len(conf),block=key[0],page=n))
    return result

def main():
    accepted=[];review=[];seen=set();raw=[]
    verified=[json.loads(line) for line in (ROOT/'verified_transcriptions.jsonl').read_text().splitlines()]
    for n in range(7,229):
        chapter=max((v for v in CHAPTERS if v[0]<=n),key=lambda v:v[0])[1]
        topic=max((v for v in TOPICS if v[0]<=n),key=lambda v:v[0])[1]
        raw.append(dict(pdf_page=n,text=(CACHE/f'page_{n:03d}.txt').read_text()))
        if n in REVISION:
            review.append(dict(pdf_page=n,chapter=chapter,text=raw[-1]['text'],reasons=['revision_page_questions_and_distractors']));continue
        for idx,v in enumerate(v for v in verified if v['page']==n):
            accepted.append(dict(v,chapter=chapter,index=-100-idx,block='manual',confidence=None))
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
            if re.search(r'(wazaelimu|Student.?s\s*Book|Physics for Secondary|READING ONLY)',t,re.I):reasons.append('boilerplate')
            if re.search(r'constant speed.{0,70}not accelerat',t,re.I):reasons.append('source_claim_requires_scientific_review_constant_speed_vs_velocity')
            if re.match(r'^(?:\d+[.)]?\s*)?(Identify and observe|Draw|Compare|State whether|Explain|Discuss|Mention|List|Outline)\b',t,re.I):reasons.append('learning_question_or_task_not_answer_evidence')
            if '=' in t or re.search(r'[²³√ρΔ→]|\b(?:kg|g|cm|m|s|N)\s*[/^]\s*(?:cm|m|s|kg)|\d\s*[×÷]\s*\d',t):reasons.append('equation_or_unit_requires_visual_verification')
            if re.match(r'^(Example|Solution|Given|Required|Substitut|Calculate|Determine|Find)\b',t,re.I):reasons.append('worked_example_or_question_requires_complete_source_verification')
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
            if reasons:review.append(dict(pdf_page=n,printed_page=n-6,chapter=chapter,topic=topic,text=t,confidence=b['confidence'],reasons=reasons));continue
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
        c=dict(id=f'physics_f1_{len(chunks)+1:04d}',source_file=PDF.name,subject='Physics',level='Form One',language='en',chapter=pending[0]['chapter'],topic=pending[0]['topic'],pdf_pages=pages,printed_pages=[p-6 for p in pages],word_count=len(content.split()),quality_status='visually_verified_transcription' if all(b.get('verification')=='visually_verified_against_source_pdf' for b in allparts) else 'ocr_screened_not_fully_manually_verified',ocr_mean_confidence_min=min((b['confidence'] for b in allparts if b['confidence'] is not None),default=None),content=content)
        c['embedding_text']=f"Physics | Form One | {c['chapter']} | {c['topic']}\n{content}";c['content_sha256']=hashlib.sha256(content.encode()).hexdigest();chunks.append(c)
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
            boundary=bool(existing) and ((cur['chapter'],cur['topic'])!=(existing[0]['chapter'],existing[0]['topic']) or cur.get('verification')!=existing[0].get('verification'))
            if boundary:flush();overlap=[]
            if sum(len(p['text'].split()) for p in pending+overlap)+len(part.split())>230:flush()
            if sum(len(p['text'].split()) for p in overlap)+len(part.split())>230:overlap=[]
            pending.append(cur)
            if sum(len(p['text'].split()) for p in pending)>=170:flush()
    flush()
    def write_jsonl(name,records):
        (ROOT/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in records),encoding='utf-8')
    write_jsonl('Physics_RAG_chunks.jsonl',chunks);write_jsonl('Physics_review_required.jsonl',review);write_jsonl('Physics_source_ocr.jsonl',raw)
    (ROOT/'Physics_RAG_chunks.txt').write_text('\n\n'.join(f"=== CHUNK {c['id']} ===\nSource: {c['source_file']}\nSubject: Physics | Level: Form One | Language: English\nChapter: {c['chapter']}\nTopic: {c['topic']}\nPDF pages: {', '.join(map(str,c['pdf_pages']))} | Printed pages: {', '.join(map(str,c['printed_pages']))}\nQuality: {c['quality_status']}\nText:\n{c['content']}\n=== END CHUNK ===" for c in chunks)+'\n',encoding='utf-8')
    clean_blocks=[]
    for b in clean:
        pages=b.get('pages',[b['page']])
        clean_blocks.append(f"[PDF pages: {','.join(map(str,pages))} | Printed pages: {','.join(str(p-6) for p in pages)} | {b['chapter']} | {b['topic']}]\n{b['text']}")
    (ROOT/'Physics_cleaned_for_RAG.txt').write_text('\n\n'.join(clean_blocks)+'\n',encoding='utf-8')
    sizes=[c['word_count'] for c in chunks]
    audit=dict(source_file=str(SRC),source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),source_pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),source_words=len(SRC.read_text().split()),ocr_pdf_pages=[7,228],ocr_page_count=len(raw),revision_pdf_pages=sorted(REVISION),chunks=len(chunks),accepted_blocks=len(clean),review_records=len(review),chunk_words_min=min(sizes),chunk_words_median=statistics.median(sizes),chunk_words_max=max(sizes),review_reason_counts=dict(collections.Counter(r for b in review for r in b['reasons'])),coverage='Filtered subset; not a complete verified transcription. Original and all re-OCR pages remain available.',visually_verified_excerpt_pdf_pages=sorted({p for v in verified for p in v['pages']}),tokenizer_counts_measured=False,embeddings_generated=False,vector_retrieval_tested=False,gemma_tested=False)
    (ROOT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
