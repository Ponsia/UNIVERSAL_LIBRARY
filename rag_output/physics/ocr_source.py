"""Re-OCR the source scan. No network access; cached page-level TSV and text."""
import os, subprocess, concurrent.futures, pathlib, io
from PIL import Image, ImageChops
PDF=pathlib.Path('/home/egovridc26/Desktop/EGA PTRACTICAL TRAINING - 0046/INDIVIDUAL HACKERTHON/UNILIBRARY/pdf_to_txt/physics_form_one.pdf')
CACHE=pathlib.Path('/tmp/physics_rag_ocr'); CACHE.mkdir(exist_ok=True)
def page(n):
    dst=CACHE/f'page_{n:03d}'
    if dst.with_suffix('.tsv').exists(): return n
    proc=subprocess.run(['pdftoppm','-f',str(n),'-l',str(n),'-scale-to','3200','-png','-singlefile',str(PDF),str(dst)],capture_output=True,check=True)
    im=Image.open(dst.with_suffix('.png')).convert('RGB'); w,h=im.size
    im=im.crop((int(w*.085),int(h*.035),int(w*.925),int(h*.94)))
    r,g,b=im.split(); mx=ImageChops.lighter(ImageChops.lighter(r,g),b); mn=ImageChops.darker(ImageChops.darker(r,g),b)
    dark=mx.point(lambda p:255 if p<185 else 0)
    neutral=ImageChops.subtract(mx,mn).point(lambda p:255 if p<95 else 0)
    bw=ImageChops.invert(ImageChops.multiply(dark,neutral));bw.save(dst.with_suffix('.png'))
    env=dict(os.environ,OMP_THREAD_LIMIT='1')
    subprocess.run(['tesseract',str(dst.with_suffix('.png')),str(dst),'--psm','3','-l','eng','txt','tsv'],env=env,capture_output=True,check=True)
    return n
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for i,n in enumerate(ex.map(page,range(7,229)),1):
            if i%10==0 or i==222: print(f'OCR complete {i}/222 (PDF page {n})',flush=True)
