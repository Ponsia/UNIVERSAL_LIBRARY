"""Build auditable RAG text/JSONL from cached Tesseract TSV. Standard library only.
OCR confidence is a screening heuristic, not proof of factual correctness.
"""
import csv,json,re,hashlib,statistics,pathlib,collections,difflib
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parent
CACHE=pathlib.Path('/tmp/biology_rag_ocr')
SOURCE=pathlib.Path('/home/egovridc26/Desktop/EGA PTRACTICAL TRAINING - 0046/INDIVIDUAL HACKERTHON/UNILIBRARY/pdf_to_txt/Biology_cleaned.txt')
CHAPTERS=[(7,'Introduction to Biology'),(16,'Scientific processes in Biology'),(42,'Cell structure and organization'),(58,'Classification of living things'),(70,'Viruses and major groups of living things'),(120,'Nutrition in plants'),(144,'Glossary')]
HEADINGS=['Basic concepts and terminologies in Biology','Life','Branches of Biology','Importance of studying Biology','Relationship between Biology and other scientific fields','Common Biology laboratory apparatus, equipment and other resources','Basic skills in scientific studies','Scientific methods','Simple biological experiments','Types of cells','Animal and plant cells','Cell differentiation','Concept of classification','Classification systems','Major groups of living things','Binomial nomenclature','Viruses','Kingdom Monera','Kingdom Protoctista','Kingdom Fungi','Kingdom Plantae','Kingdom Animalia','Classes of the division Angiospermophyta','Concept of nutrition','Photosynthesis','Structure of the leaf in relation to photosynthesis','Importance of photosynthesis','Essential and non-essential elements in plants','The cell','Cytoplasm','Cytroplasm','Cell membrane','Nucleus','Cell vacuoles','Mitochondria','Cell wall','Chloroplasts','Vacuole','Length','Mass','Temperature','Volume','Observation','Measurement','Experimentation','Hypothesis','Conclusion','Reporting results','Data analysis and interpretation','Relationship between Biology and other fields of science','Agriculture','Medicine and Pharmacy','Nutrition','Forestry','Biological models','Preserved specimens','Cage','Aquarium','The microscope','The light microscope','The electron microscope','External structure of a leaf','Internal structure of a leaf','Class Monocotyledoneae','Class Dicotyledoneae','Stages of photosynthesis','Light reaction','Dark reaction']
PRESERVE={'micro-organisms','micro-organism','non-living','higher-yielding','disease-resistant','sub-branches','single-celled','multi-cellular','cross-pollination','self-pollination','cold-blooded','warm-blooded','oxygen-carrying','free-living','membrane-bound'}
def clean(text):
    text=text.translate(str.maketrans({'‘':"'",'’':"'",'“':'"','”':'"','—':'-','–':'-'}))
    def dehyphen(m):
        a,b=m.groups();return a+'-'+b if (a+'-'+b).lower() in PRESERVE else a+b
    text=re.sub(r'([A-Za-z]+)-\s*\n\s*([a-z]+)',dehyphen,text)
    text=re.sub(r'(?<=\w)\s*\|\s*',' ',text)
    text=re.sub(r'\b1s\b','is',text)
    for a,b in {'studics':'studies','cxamples':'examples','Ithelps':'It helps','trealing':'treating','fromthe':'from the'}.items():text=text.replace(a,b)
    text=text.replace('first cure discovered for quinine','first cure discovered for malaria was quinine')
    return re.sub(r'\s+',' ',text).strip(' |~_')
def blocks(n):
    center=Image.open(CACHE/f'page_{n:03d}.png').width/2
    groups=collections.OrderedDict()
    with (CACHE/f'page_{n:03d}.tsv').open() as f:
        for row in csv.DictReader(f,delimiter='\t'):
            if row['level']=='5' and row['text'].strip():
                groups.setdefault((row['block_num'],row['par_num']),[]).append(row)
    out=[]
    for rows in groups.values():
        lines=collections.OrderedDict()
        for r in rows: lines.setdefault(r['line_num'],[]).append(r)
        # Restore two columns accidentally combined into the same OCR block.
        splits=[]
        for line in lines.values():
            split=None
            for i in range(1,len(line)):
                prev,cur=line[i-1],line[i]
                edge=int(prev['left'])+int(prev['width']);start=int(cur['left'])
                if edge<center<start and start-edge>45: split=i;break
            splits.append(split)
        merged=any(x is not None for x in splits) and not any(any(int(r['left'])<center<int(r['left'])+int(r['width']) for r in line) for line in lines.values())
        sets=[]
        if merged:
            for side in (0,1):
                collected=[]
                for line,k in zip(lines.values(),splits):
                    if k is not None: collected.extend(line[:k] if side==0 else line[k:])
                    elif (statistics.mean(int(r['left']) for r in line)<center)==(side==0): collected.extend(line)
                sets.append(collected)
        else: sets=[rows]
        for rr in sets:
            if not rr:continue
            ll=collections.OrderedDict()
            for r in rr:ll.setdefault(r['line_num'],[]).append(r['text'])
            txt=clean('\n'.join(' '.join(v) for v in ll.values()))
            conf=[float(r['conf']) for r in rr if float(r['conf'])>=0]
            out.append((txt,round(statistics.mean(conf),2),sum(v<65 for v in conf)/len(conf)))
    return out

def main():
    accepted=[];review=[];topic='Basic concepts and terminologies in Biology';exercise=False
    seen=set()
    for n in range(7,148):
        ch=max((x for x in CHAPTERS if x[0]<=n),key=lambda x:x[0])[1]
        if n in [x[0] for x in CHAPTERS]:topic=ch;exercise=False
        if n in set(range(14,16))|set(range(39,42))|set(range(56,58))|set(range(68,70))|set(range(117,120))|set(range(141,144)):
            review.append(dict(text=(CACHE/f'page_{n:03d}.txt').read_text(),pdf_page=n,printed_page=n-6,chapter=ch,reasons=['revision_page_contains_questions_and_true_false_distractors']))
            continue
        if n==9:
            # Verified against the rendered source page; preserve row associations.
            text='Other branches of Biology:\n'+ '\n'.join(f'{a}: {b}.' for a,b in [('Anatomy','Body structures of organisms'),('Cytology','Structure and functions of cells'),('Ecology','Relationship between organisms and their environment'),('Entomology','Insects'),('Genetics','Heredity and variation'),('Immunology','Immune systems'),('Mycology','Fungi'),('Parasitology','Parasites'),('Taxonomy','Classification of organisms'),('Physiology','Physical and chemical processes taking place within living organisms')])
            accepted.append(dict(text='Microbiologist. However, there are many sub-branches of Biology that deal with different aspects of living things. Examples are given in Table 1.1.',pages=[9],chapter=ch,topic='Basic concepts and terminologies in Biology',confidence=100,verification='visually_verified_transcription'))
            accepted.append(dict(text=text,pages=[n],chapter=ch,topic='Branches of Biology',confidence=100,verification='visually_verified_transcription'))
            topic='Importance of studying Biology';exercise=False
            continue
        for block_idx,(text,confidence,low) in enumerate(blocks(n)):
            if not text:continue
            if text.startswith('Activity'):
                topic=text.split('Materials:')[0].strip()
                exercise=False
            base=dict(text=text,pdf_page=n,printed_page=n-6,chapter=ch,ocr_mean_confidence=confidence)
            heading=next((h for h in HEADINGS if text.casefold()==h.casefold()),None)
            if not heading and len(text.split())<=12:
                matches=difflib.get_close_matches(text.casefold(),[h.casefold() for h in HEADINGS],n=1,cutoff=.9)
                if matches:heading=HEADINGS[[h.casefold() for h in HEADINGS].index(matches[0])]
            if heading:topic=heading;exercise=False;continue
            if re.match(r'^(Revision\s+exercise|Exercise)\b',text,re.I):exercise=True
            reasons=[]
            if exercise:reasons.append('exercise_or_question_section')
            if re.match(r'^(Task\s+\d|Search from|Search for|From .*sources|Read from|Write TRUE|Go through|Relate Biology|Explain the fields|Figure\s|Fig\s|Table\s)',text,re.I):reasons.append('task_caption_or_table_requires_layout_review')
            if re.search(r'\b(Outline|Mention|Describe|Differentiate|Explain why|Give any|List down|Name the gas|Your teacher asks|As a Biology student|You are working|You are leading)\b',text,re.I):reasons.append('question_or_instruction_not_answer_evidence')
            if 'In this chapter' in text or 'competencies developed' in text:reasons.append('introductory_learning_objectives')
            if re.search(r'(10%|15%|Magnification of a drawing =|UG my|Seal The|1\. I)',text):reasons.append('observed_layout_or_ocr_corruption')
            if '?' in text:reasons.append('question_not_answer_evidence')
            if len(text.split())<3:reasons.append('short_label_or_unrecognised_heading')
            if confidence<88 or low>.12:reasons.append('low_ocr_confidence')
            if re.search(r'[\\|{}<>]|[A-Za-z][@©][A-Za-z]',text):reasons.append('suspicious_ocr_symbols')
            if re.search(r'(wazaelimu|Student.s Book|Biology for Secondary|READING ONLY)',text,re.I):reasons.append('boilerplate')
            if text in seen:reasons.append('duplicate')
            if reasons:review.append(dict(base,reasons=reasons));continue
            seen.add(text)
            accepted.append(dict(text=text,pages=[n],chapter=ch,topic=topic,confidence=confidence,verification='ocr_screened_not_fully_manually_verified',block_idx=block_idx))
    # Rejoin interrupted sentences only within the same section, without crossing removed blocks.
    merged=[]
    for p in accepted:
        if merged and p['topic']==merged[-1]['topic'] and p['chapter']==merged[-1]['chapter'] and p['pages'][0]-merged[-1]['pages'][-1]<=1 and not re.search(r'[.!?:]$',merged[-1]['text']) and (p['pages'][0]>merged[-1]['pages'][-1] or p.get('block_idx',-99)==merged[-1].get('block_idx',-1)+1):
            prev=merged[-1];prev['text']+=' '+p['text'];prev['pages']=sorted(set(prev['pages']+p['pages']));prev['confidence']=min(prev['confidence'],p['confidence']);prev['block_idx']=p.get('block_idx',-1)
        else:merged.append(p.copy())
    screened=[]
    for p in merged:
        text=p['text']
        # Cut off interrupted trailing sentences rather than expose them as answer evidence.
        if not re.search(r'[.!?]$',text):
            ends=list(re.finditer(r'[.!?](?:\s|$)',text))
            cutoff=ends[-1].end() if ends else 0
            tail=text[cutoff:].strip()
            if tail: review.append(dict(text=tail,pdf_page=p['pages'][0],chapter=p['chapter'],reasons=['incomplete_sentence_requires_source_review']))
            text=text[:cutoff].strip()
        if text and re.match(r'^(?:[A-Z]|\([a-z]\)|\d+[.)])',text) and len(text.split())>=8:
            screened.append(dict(p,text=text))
        elif text: review.append(dict(text=text,pdf_page=p['pages'][0],chapter=p['chapter'],reasons=['fragment_or_label_requires_source_review']))
    merged=screened
    chunks=[];pending=[];overlap=[]
    def emit():
        nonlocal pending,overlap
        if not pending:return
        parts=overlap+pending
        content='\n\n'.join(x['text'] for x in parts)
        if chunks and content==chunks[-1]['content']:pending=[];return
        pages=sorted({n for p in parts for n in p['pages']})
        chunk=dict(id=f'biology_f1_{len(chunks)+1:04d}',source_file='Biology.pdf',subject='Biology',level='Form One',language='en',chapter=pending[0]['chapter'],topic=pending[0]['topic'],pdf_pages=pages,printed_pages=[n-6 for n in pages],word_count=len(content.split()),ocr_mean_confidence_min=min(p['confidence'] for p in parts),quality_status='ocr_screened_not_fully_manually_verified',content=content)
        chunk['embedding_text']=f"Biology | Form One | {chunk['chapter']} | {chunk['topic']}\n{content}"
        chunk['content_sha256']=hashlib.sha256(content.encode()).hexdigest()
        chunks.append(chunk)
        last=pending[-1]
        sentences=re.split(r'(?<=[.!?])\s+',last['text']);tail=sentences[-1]
        overlap=[dict(last,text=tail)] if 8<=len(tail.split())<=35 else []
        pending=[]
    for p in merged:
        sentences=re.split(r'(?<=[.!?])\s+',p['text']);parts=[];buffer=''
        for s in sentences:
            if len(s.split())>210:
                # Explicitly mark hard splits; do not pretend these are complete sentences.
                ws=s.split();parts.extend(' '.join(ws[i:i+200]) for i in range(0,len(ws),200));continue
            if len((buffer+' '+s).split())>210:
                if buffer:parts.append(buffer)
                buffer=s
            else:buffer=(buffer+' '+s).strip()
        if buffer:parts.append(buffer)
        for part in parts:
            pp=dict(p,text=part)
            existing=pending or overlap
            boundary=bool(existing) and (pp['topic'],pp['chapter'])!=(existing[0]['topic'],existing[0]['chapter'])
            size=sum(len(x['text'].split()) for x in pending+overlap)+len(part.split())
            if boundary or size>230:
                emit()
                if boundary:overlap=[]
                if sum(len(x['text'].split()) for x in overlap)+len(part.split())>230:overlap=[]
            pending.append(pp)
            if sum(len(x['text'].split()) for x in pending)>=175:emit()
    emit()
    def jsonl(name,records):
        (ROOT/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    jsonl('Biology_RAG_chunks.jsonl',chunks);jsonl('Biology_review_required.jsonl',review)
    (ROOT/'Biology_RAG_chunks.txt').write_text('\n\n'.join(f"=== CHUNK {c['id']} ===\nSource: {c['source_file']}\nSubject: Biology | Level: Form One | Language: English\nChapter: {c['chapter']}\nTopic: {c['topic']}\nPDF pages: {', '.join(map(str,c['pdf_pages']))} | Printed pages: {', '.join(map(str,c['printed_pages']))}\nQuality: OCR screened; full manual verification pending\nText:\n{c['content']}\n=== END CHUNK ===" for c in chunks)+'\n',encoding='utf-8')
    (ROOT/'Biology_cleaned_for_RAG.txt').write_text('\n\n'.join(f"[PDF page(s): {','.join(map(str,p['pages']))} | Chapter: {p['chapter']} | Topic: {p['topic']}]\n{p['text']}" for p in merged)+'\n',encoding='utf-8')
    sizes=[c['word_count'] for c in chunks]
    audit=dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),source_words=len(SOURCE.read_text().split()),pages_ocr=141,pdf_pages_range=[7,147],chunks=len(chunks),unique_accepted_blocks=len(merged),review_blocks=len(review),chunk_words_min=min(sizes),chunk_words_median=statistics.median(sizes),chunk_words_max=max(sizes),review_reasons=dict(collections.Counter(r for x in review for r in x['reasons'])),note='Word counts are not tokenizer counts. OCR confidence cannot guarantee correct reading order, facts, or table alignment. Excluded passages remain in review file.')
    (ROOT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
