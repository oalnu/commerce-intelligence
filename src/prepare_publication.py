"""Create a reviewable source-only publication candidate; never upload or publish.

Leaves working files untouched. Omits imported PBIX data, caches, row-level audit
extracts and private investigation history. A deliberate placeholder replaces
the local M parameter. The owner must decide licence/privacy questions first.
"""
import argparse
import json
import hashlib
import re
import shutil
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crop-screenshots',action='store_true',help='Owner-authorized pixel-exact canvas crops; requires Pillow from requirements-artifacts.txt.')
    args=parser.parse_args()
    name='publication-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'dist'/name
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    omit={'__pycache__','.pbi'}
    for folder in ['src','sql','tests','config','docs','assets','reports','output','powerbi']:
        for p in (ROOT/folder).rglob('*'):
            relative=p.relative_to(ROOT)
            if not p.is_file() or any(x in omit for x in relative.parts) or p.suffix=='.pbix':continue
            if p.name in {'source_exceptions.csv','payment_reconciliation.csv','analysis_results.json','publication_preparation.json','artifact_inventory.json','inventory_artifacts.py','final_review_checks.py','final_review_checks.json'}:continue
            target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    for name in ['README.md','DATA_LICENSE.md','.gitignore','.gitattributes',
                 'requirements.txt','requirements-dev.txt','requirements-artifacts.txt','RELEASE_NOTES.md','LICENSE']:
        shutil.copy2(ROOT/name,out/name)
    m=out/'powerbi/CommerceIntelligence.SemanticModel/definition/expressions.tmdl'
    value=m.read_text(encoding='utf-8')
    value=re.sub(r'expression DataRoot = "[^"\r\n]*"','expression DataRoot = "__SET_DATA_ROOT_OR_RUN_PIPELINE__"',value,count=1)
    m.write_text(value,encoding='utf-8')
    if args.crop_screenshots:
        from PIL import Image
        manifest=json.loads((ROOT/'reports/powerbi/screenshot_manifest.json').read_text())
        for record in manifest['screenshots']:
            source=ROOT/record['file']
            if hashlib.sha256(source.read_bytes()).hexdigest()!=record['sha256']:
                raise ValueError(f'Source screenshot does not match recorded evidence: {source.name}')
            with Image.open(source) as shot:
                if shot.size!=(1710,1021):raise ValueError('Reinspect screenshot dimensions before cropping')
                box=(112,160,1536,961)
                cropped=shot.crop(box)
                cropped.save(out/record['file'])
                with Image.open(out/record['file']) as check:
                    if check.size!=(1424,801) or check.tobytes()!=cropped.tobytes():
                        raise ValueError('Crop pixel verification failed')
            record['original_capture_sha256']=record['sha256']
            record['original_capture_dimensions']=[1710,1021]
            record['crop_box_left_top_right_bottom']=list(box)
            target=out/record['file']
            record['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            record['bytes']=target.stat().st_size
        manifest['image_edits']='Owner-authorized pixel-exact crop to report canvas; no rescaling, retouching or generated pixels.'
        manifest['note']='Original full-window captures remain local. Published files are verified crops; DAX evidence separately checks totals.'
        (out/'reports/powerbi/screenshot_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # The source package intentionally has no populated PBIX. Remove any old link.
    readme=out/'README.md'
    readme.write_text(readme.read_text(encoding='utf-8-sig').replace('[Open populated PBIX](powerbi/CommerceIntelligence.pbix)','Populated PBIX retained locally pending release review'),encoding='utf-8')
    note='''# Publication candidate - owner review required

This source-only package was generated locally. Nothing was uploaded.
Run src/run.py to obtain pinned data and regenerate a local DataRoot, then open
the PBIP and perform the documented Desktop checks. The placeholder PBIP itself
is not ready to refresh. This sanitized copy was schema-checked; it has not been
independently opened in Desktop. Working report evidence refers to the local build.

The imported PBIX, raw/processed data, row-level audit extracts and local caches
are intentionally omitted. Screenshot/summary outputs remain data-derived and
subject to the source licence. Real screenshots include the signed-in user's
display name in Desktop chrome: decide whether to share them before publishing.
Review DATA_LICENSE.md and docs/publication.md before any public release.
'''
    # Publication status belongs in release notes; historical audit remains dated.
    if not args.crop_screenshots:
        (out/'PUBLICATION_CANDIDATE.md').write_text(note,encoding='utf-8')
    broken=[]
    for p in out.rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
            if not re.match(r'https?://',link) and not (p.parent/link.split('#')[0]).exists():
                broken.append([p.relative_to(out).as_posix(),link])
    if broken:raise ValueError(f'Broken candidate documentation links: {broken}')
    forbidden=[]
    for p in out.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.py','.sql','.md','.json','.tmdl','.ps1','.pbip','.pbir','.pbism'}:
            text=p.read_text(encoding='utf-8-sig')
            if re.search(r'[A-Za-z]:[/\\]Users[/\\][^/\\" ]+|[\w.+-]+@student\.[\w.-]+',text,re.I):forbidden.append(p.relative_to(out).as_posix())
    if forbidden:raise ValueError(f'Local identity/path remains in publication text: {forbidden}')
    # Validate the actual copied candidate, not just the working definitions.
    try:
        import validate_report_schema
    except ModuleNotFoundError as exc:
        raise RuntimeError('Publication checks require requirements-dev.txt') from exc
    validate_report_schema.ROOT=out
    validate_report_schema.main()
    file_manifest=[]
    for p in sorted(out.rglob('*')):
        if p.is_file():
            with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
            file_manifest.append({'file':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':digest})
    (out/'publication_manifest.json').write_text(json.dumps({'files':file_manifest,'note':'Candidate hashes after path sanitization; manifest excludes itself.'},indent=2)+'\n')
    record={'status':'PREPARED_NOT_PUBLISHED','created_utc':datetime.now(timezone.utc).isoformat(),
            'candidate':out.relative_to(ROOT).as_posix(),'pbix_included':False,'local_m_path_replaced':True,
            'screenshots_cropped':args.crop_screenshots,
            'known_limits':(['Screenshot chrome contains display name'] if not args.crop_screenshots else [])+['CC BY-NC-SA terms apply','Placeholder source package requires regeneration and Desktop validation']}
    (ROOT/'reports/validation/publication_preparation.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()

