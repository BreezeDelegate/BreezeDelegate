#!/usr/bin/env python3
"""Generate small public-profile language charts from the existing GitHub metrics SVG.

This script deliberately reuses the aggregate values already selected by
scripts/render_metrics.py. It never queries or discloses private repo names.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import html
from pathlib import Path
import re

PUBLIC_RE = re.compile(r'<div class="field language details">(.*?)</small>\s*</div>',re.S)
LANG_RE = re.compile(r'</svg>\s*([^<>\n]+?)\s*</div>',re.S)
PERCENT_RE = re.compile(r'<small>\s*<div>[^<>]*</div>\s*<div>\s*([\d.]+)%\s*</div>',re.S)
COLOR_RE = re.compile(r'<path\s+fill="(#[A-Fa-f0-9]{6})"')
PRIVATE_RE = re.compile(r'<span\s+style="[^"]*background:(#[A-Fa-f0-9]{6})[^"]*"\s*></span>\s*<span>\s*([^<>]+?)\s+([\d.]+)%\s*</span>',re.S)


def read_source(svg: str):
    public=[]
    for sec in PUBLIC_RE.findall(svg):
        label=LANG_RE.search(sec)
        pct=PERCENT_RE.search(sec)
        color=COLOR_RE.search(sec)
        if not (label and pct and color):
            continue
        public.append((label.group(1).strip(),float(pct.group(1)),color.group(1)))
    if not public or abs(sum(x[1] for x in public)-100)<0.001:
        # The source often has an implicit remainder; exact 100% is also possible.
        if not public: raise ValueError('No public language statistics found')
    if sum(x[1] for x in public)>100.5:
        raise ValueError('Public language shares total more than 100%')
    if sum(x[1] for x in public)<99.8:
        public.append(('Other',round(100-sum(x[1] for x in public),2),'#8b949e'))
    # Private aggregate text appears before the public language block.
    ix=svg.find('Private languages')
    if ix<0: raise ValueError('Missing private repository language aggregate')
    private_html=svg[ix:svg.find('Most used languages',ix)]
    private=[(name.strip(),float(pct),color) for color,name,pct in PRIVATE_RE.findall(private_html)]
    if not private or not 99<=sum(x[1] for x in private)<=101:
        raise ValueError('Missing/invalid private language aggregate')
    if len({x[0] for x in public})!=len(public):raise ValueError('Duplicate public language')
    return public,private


def render_svg(public,private,dark:bool,mobile:bool,dated:str):
    bg='#0D1117' if dark else '#FFFFFF'
    fg='#E6EDF3' if dark else '#24292F'
    subtle='#8B949E' if dark else '#59636E'
    line='#30363D' if dark else '#D0D7DE'
    track='#21262D' if dark else '#F0F2F5'
    W=430 if mobile else 860
    H=410 if mobile else 258
    font='-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif'
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
       '<title id="title">Language activity</title>',
       '<desc id="desc">Public code share by detected lines of code; private aggregate share by primary repository language. These measures differ.</desc>',
       f'<rect width="{W}" height="{H}" fill="{bg}"/>']
    def txt(x,y,t,size=12,color=fg,weight=400,anchor=None):
        extra=f' text-anchor="{anchor}"' if anchor else ''
        p.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{color}"{extra}>{html.escape(t)}</text>')
    def rule(y):p.append(f'<path d="M0 {y}H{W}" stroke="{line}"/>')
    def bar(items,y):
        x=0.
        p.append(f'<rect x="0" y="{y}" width="{W}" height="12" fill="{track}"/>')
        for n,v,c in items:
            bw=W*v/100.
            if bw<=0:continue
            p.append(f'<rect x="{x:.2f}" y="{y}" width="{bw:.2f}" height="12" fill="{c}"/>');x+=bw
    def legend(items,xs,ybase,colcount,step,fontsize=12):
        for i,(n,v,c) in enumerate(items):
            col=i%colcount;row=i//colcount;xx=xs[col];yy=ybase+step*row
            p.append(f'<circle cx="{xx+4}" cy="{yy-4}" r="4" fill="{c}"/>')
            txt(xx+13,yy,f'{n} {v:g}%',fontsize,fg)
    if mobile:
        txt(0,22,'Language activity',17,fg,650)
        txt(0,44,'Snapshot · '+dated,11,subtle)
        rule(57)
        txt(0,78,'Public code',14,fg,600)
        txt(0,96,'Share of detected code lines',11,subtle)
        bar(public,107)
        legend(public,[0,150],144,2,24,11)
        rule(257)
        txt(0,279,'Private repositories',14,fg,600)
        txt(0,297,'Share by primary language',11,subtle)
        bar(private,310)
        legend(private,[0,205],340,2,23,11)
        txt(0,389,'Different measures; not a skill ranking.',10,subtle)
    else:
        txt(0,18,'Language activity',14,fg,650)
        txt(W,18,'Snapshot · '+dated,11,subtle,anchor='end')
        rule(30)
        txt(0,54,'Public code',12,fg,600)
        txt(W,54,'Share of detected code lines',11,subtle,anchor='end')
        bar(public,67)
        xs=[0,180,335,490,690]
        legend(public[:9],xs,104,5,23,12)
        rule(140)
        txt(0,160,'Private repositories',12,fg,600)
        txt(W,160,'Share by primary repository language',11,subtle,anchor='end')
        bar(private,174)
        legend(private[:4],[0,210,420,625],213,4,22,12)
        rule(231)
        txt(0,250,'Public lines and private repository counts use different measures. Not a skill ranking.',11,subtle)
    p.append('</svg>')
    return ''.join(p)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('github-metrics.svg'))
    parser.add_argument('--output-dir',type=Path,default=Path('assets'))
    parser.add_argument('--date',default=datetime.now().strftime('%-d %b %Y'))
    args=parser.parse_args()
    public,private=read_source(args.input.read_text(encoding='utf8'))
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for mobile in (False,True):
        for mode in ('dark','light'):
            f=args.output_dir/('language-footprint-'+('mobile-' if mobile else '')+mode+'.svg')
            f.write_text(render_svg(public,private,mode=='dark',mobile,args.date),encoding='utf8')
    print('Wrote 4 language activity graphics')

if __name__=='__main__': main()
