"""Exercise the complete pipeline in a new project directory, starting without data.

Use --archive for an offline original ZIP; otherwise download the pinned source.
The caller's working model, source data and Power BI files are never rewritten.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main(archive=None):
    started=time.perf_counter()
    destination=ROOT/'.cache'/f'cleanroom-{uuid.uuid4().hex}'
    destination.mkdir(parents=True)
    for folder in ['src','sql','config']:
        shutil.copytree(ROOT/folder,destination/folder,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'assets/powerbi_seed',destination/'assets/powerbi_seed')
    cmd=[sys.executable,str(destination/'src/run.py')]
    if archive:cmd += ['--archive',str(Path(archive).resolve())]
    result=subprocess.run(cmd,cwd=destination,capture_output=True,text=True)
    (destination/'execution.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(f'Clean-room pipeline failed; see {destination}/execution.log')
    before=json.loads((ROOT/'reports/validation/build_manifest.json').read_text())
    after=json.loads((destination/'reports/validation/build_manifest.json').read_text())
    expected={k:v['sha256'] for k,v in before['exports'].items()}
    actual={k:v['sha256'] for k,v in after['exports'].items()}
    if actual!=expected:raise ValueError('Clean-room mart hashes differ')
    if len(list((destination/'reports/analysis').glob('0*.json')))!=7:raise ValueError('Missing analytical outputs')
    if not (destination/'powerbi/CommerceIntelligence.pbip').exists():raise ValueError('Missing generated report project')
    evidence={'status':'PASS','started_with_raw_data':False,'archive_mode':'local pinned ZIP' if archive else 'official download',
              'steps':['ingestion','32 SQL checks','seven analytical queries','independent order validation','raw cohort audit','PBIP generation'],
              'identical_marts':len(actual),'elapsed_seconds':round(time.perf_counter()-started,2),
              'limits':'Reuses the installed Python environment; dependency installation and Power BI Desktop are separate checks.'}
    (ROOT/'reports/validation/cleanroom.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive');args=parser.parse_args()
    main(args.archive)
