"""Render the project architecture as original SVG and PNG, never dashboard evidence."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
W,H=1600,750
INK='#142E42';TEAL='#147D78';PALE='#F1F5F7';MUTED='#607582';ORANGE='#D56B42'

def font(size,bold=False):
    for candidate in [Path('C:/Windows/Fonts')/('segoeuib.ttf' if bold else 'segoeui.ttf'),Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]:
        if candidate.exists():return ImageFont.truetype(str(candidate),size)
    return ImageFont.load_default(size=size)

def main():
    im=Image.new('RGB',(W,H),PALE);d=ImageDraw.Draw(im)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="{PALE}"/>']
    def text(x,y,value,size=22,color=INK,bold=False):
        d.text((x,y),value,font=font(size,bold),fill=color)
        svg.append(f'<text x="{x}" y="{y+size}" font-family="Segoe UI, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')
    def box(x,y,w,h,title,lines,color=TEAL):
        d.rounded_rectangle((x,y,x+w,y+h),radius=14,fill='white',outline='#D6E1E6',width=2)
        d.rectangle((x+15,y+20,x+20,y+h-20),fill=color)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="white" stroke="#D6E1E6" stroke-width="2"/><rect x="{x+15}" y="{y+20}" width="5" height="{h-40}" fill="{color}"/>')
        text(x+36,y+22,title,25,bold=True)
        for i,line in enumerate(lines):text(x+36,y+67+i*30,line,21,MUTED)
    def arrow(x1,y1,x2,y2):
        d.line((x1,y1,x2,y2),fill=TEAL,width=4)
        if y1==y2:points=[(x2,y2),(x2-12,y2-7),(x2-12,y2+7)]
        else:points=[(x2,y2),(x2-7,y2-12),(x2+7,y2-12)]
        d.polygon(points,fill=TEAL)
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{TEAL}" stroke-width="4"/><polygon points="'+ ' '.join(f'{x},{y}' for x,y in points)+f'" fill="{TEAL}"/>')
    text(55,34,'COMMERCE INTELLIGENCE',18,TEAL,True)
    text(55,70,'A local pipeline with independent checks',38,bold=True)
    text(55,128,'Real Olist data  /  fixed source hashes  /  no cloud or trial dependency',23,MUTED)
    box(55,200,325,195,'01  Source + ingest',['9 authentic Olist CSVs','Pinned SHA-256 + schema','Python download / extraction'])
    arrow(385,292,434,292)
    box(440,200,325,195,'02  DuckDB SQL',['Raw > typed core > marts','Aggregate children first','32 integrity checks'])
    arrow(770,292,819,292)
    box(825,200,325,195,'03  Import model',['9 ordered CSV exports','Order + item facts','Explicit DAX + 7 relations'])
    arrow(1155,292,1204,292)
    box(1210,200,335,195,'04  Power BI',['Two interactive pages','PBIP source + loaded PBIX','Real Desktop captures'])
    arrow(602,400,602,463);arrow(987,400,987,463)
    box(440,470,710,153,'Independent verification',['CSV + Decimal: 99,441 orders and 565 month/state slices','Fresh rebuild hashes + live Desktop DAX reconciliation'],ORANGE)
    text(55,674,'Evidence: quality ledgers, query results, validation JSON and untouched report screenshots.',22,MUTED)
    svg.append('</svg>')
    (ROOT/'assets').mkdir(exist_ok=True)
    im.save(ROOT/'assets/architecture.png')
    (ROOT/'assets/architecture.svg').write_text(''.join(svg),encoding='utf-8')
    print('Created assets/architecture.png and assets/architecture.svg')

if __name__=='__main__':main()
