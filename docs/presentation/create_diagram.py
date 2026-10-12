from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape

OUT = Path(__file__).parent / 'UniLib_Conceptual_Diagram.pptx'
NS='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
EMU=914400
slides=[]

def shape(i,x,y,w,h,text,fill='FFFFFF',size=19,color='183247',bold=False,geom='roundRect',line='C9D9E6'):
    paras=''.join(f'<a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="{size*100}" b="{int(bold)}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Calibri"/></a:rPr><a:t>{escape(t)}</a:t></a:r><a:endParaRPr lang="en-US"/></a:p>' for t in text.split('\n'))
    return f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Editable shape {i}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{int(x*EMU)}" y="{int(y*EMU)}"/><a:ext cx="{int(w*EMU)}" cy="{int(h*EMU)}"/></a:xfrm><a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln></p:spPr><p:txBody><a:bodyPr wrap="square" anchor="ctr" lIns="100000" rIns="100000" tIns="60000" bIns="60000"/><a:lstStyle/>{paras}</p:txBody></p:sp>'

def slide(title,subtitle):
    s=[shape(2,.4,.25,12.5,.6,title,'F4F8FC',30,'144A80',True,line='F4F8FC'),shape(3,.4,.95,12.5,.45,subtitle,'F4F8FC',16,line='F4F8FC')]
    return s

def box(s,*args,**kwargs): s.append(shape(len(s)+2,*args,**kwargs))
def arrow(s,x,y,w=.45,h=.3,down=False): box(s,x,y,w,h,'',fill='2585D6',geom='downArrow' if down else 'rightArrow',line='2585D6')
def finish(s,n):
    box(s,.45,7.03,12.4,.25,f'UniLib  |  Conceptual diagram  |  {n} / 3','F4F8FC',11,'60768A',line='F4F8FC')
    slides.append(f'<p:sld xmlns:p="{NS}" xmlns:a="{A}" xmlns:r="{R}"><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="F4F8FC"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>{"".join(s)}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')

s=slide('UniLib — System Overview','An Android study assistant that answers questions using Form 1 TIE textbooks.')
box(s,.55,1.65,3.2,.55,'ONLINE: FIRST-TIME SETUP','DAEAFB',17,'144A80',True)
box(s,.55,2.4,3.2,1.05,'SMS service\nAccess token sent to student',size=18)
box(s,.55,3.8,3.2,1.15,'Hugging Face\nAI models + tokenizer',size=18)
box(s,4.5,1.65,8.25,4.95,'','E8F3FF',line='A4C8E9')
box(s,4.7,1.8,7.8,.5,'ON THE STUDENT’S ANDROID PHONE','E8F3FF',19,'144A80',True,line='E8F3FF')
box(s,4.95,2.6,3.05,1.1,'Student\nTypes or speaks a question',size=18)
arrow(s,8.1,2.99)
box(s,8.7,2.6,3.55,1.1,'UniLib app\nFlutter interface + chat',size=18)
arrow(s,10.25,3.84,.32,.4,True)
box(s,8.7,4.4,3.55,1.25,'Local AI engine\nFind textbook excerpts\nGenerate an answer',size=18)
box(s,4.95,4.4,3.05,1.25,'Local vector database\nBiology • Chemistry • Physics',size=17)
arrow(s,8.1,4.85)
arrow(s,3.88,4.18,.46,.3)
box(s,.55,5.35,3.2,1.25,'Bundled TIE textbook text\n451 screened chunks\nIndexed during setup',size=17)
box(s,4.95,5.96,7.3,.4,'After setup: textbook search and AI answers run offline.','E8F3FF',16,'144A80',line='E8F3FF')
finish(s,1)

s=slide('UniLib — Student Journey','A simple path from registration to offline study.')
steps=[('1. Sign up','Username + phone number'),('2. Receive SMS','Model access token'),('3. Select model','UniLib Lite'),('4. Prepare app','Enter token; download AI')]
for j,(a,b) in enumerate(steps):
    x=.55+j*3.2
    box(s,x,1.85,2.65,1.3,a+'\n'+b,'FFFFFF',19,bold=False)
    if j<3: arrow(s,x+2.74,2.35,.36,.28)
arrow(s,11.3,3.35,.34,.55,True)
box(s,9.55,4.12,3.1,1.35,'5. Select Form 1\nBiology, Chemistry, Physics',size=19)
box(s,5.4,4.12,3.1,1.35,'6. Open chat\nAsk a study question',size=19)
box(s,1.25,4.12,3.1,1.35,'7. Study offline\nAnswer + textbook references',size=19)
box(s,8.65,4.63,.6,.3,'←','F4F8FC',27,'2585D6',line='F4F8FC')
box(s,4.5,4.63,.6,.3,'←','F4F8FC',27,'2585D6',line='F4F8FC')
box(s,.8,6.05,11.7,.55,'Current scope: Lite + Form 1 active  |  Pro, Max and Forms 2–6: coming soon','DAEAFB',17,'144A80')
finish(s,2)

s=slide('UniLib — How an Answer Is Produced','RAG = Retrieval-Augmented Generation: find relevant textbook text before answering.')
items=[('Student question','Text or speech converted to text'),('Understand the question','EmbeddingGemma creates a query vector'),('Search the textbooks','SQLite vector database finds relevant excerpts'),('Write the answer','Gemma 3 1B uses the selected excerpts')]
for j,(a,b) in enumerate(items):
    x=.55+j*3.2
    box(s,x,2.05,2.65,1.65,a+'\n\n'+b,size=18)
    if j<3: arrow(s,x+2.73,2.73,.38,.3)
arrow(s,11.25,3.94,.35,.5,True)
box(s,8.65,4.75,4.1,1.1,'Student receives\nAnswer + textbook page references','DAEAFB',19,'144A80')
box(s,.55,4.5,7.35,1.45,'TEXTBOOK PREPARATION\nTIE books → OCR + cleaning → text chunks\nEmbeddingGemma → local SQLite vector database',size=19)
box(s,.75,6.25,11.85,.4,'If the retrieved books do not contain enough evidence, the app reports that information was not found.','F4F8FC',15,'60768A',line='F4F8FC')
finish(s,3)

relsns='http://schemas.openxmlformats.org/package/2006/relationships'
def rels(entries): return f'<Relationships xmlns="{relsns}">'+''.join(f'<Relationship Id="{i}" Type="{t}" Target="{target}"/>' for i,t,target in entries)+'</Relationships>'
base='http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
ct='http://schemas.openxmlformats.org/package/2006/content-types'
with ZipFile(OUT,'w',ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml',f'<Types xmlns="{ct}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'+''.join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1,4))+'</Types>')
    z.writestr('_rels/.rels',rels([('rId1',base+'officeDocument','ppt/presentation.xml')]))
    z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{NS}" xmlns:a="{A}" xmlns:r="{R}"><p:sldIdLst>'+''.join(f'<p:sldId id="{255+i}" r:id="rId{i}"/>' for i in range(1,4))+'</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
    z.writestr('ppt/_rels/presentation.xml.rels',rels([(f'rId{i}',base+'slide',f'slides/slide{i}.xml') for i in range(1,4)]))
    for i,s in enumerate(slides,1): z.writestr(f'ppt/slides/slide{i}.xml',s)
print(OUT)
