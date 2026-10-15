"""Build a new empty database and require identical sorted mart exports."""
import json
import sys
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build import build, digest
from validate_independent import run

if __name__=='__main__':
    before=json.loads((ROOT/'reports/validation/build_manifest.json').read_text())
    expected={k:v['sha256'] for k,v in before['exports'].items()}
    database=ROOT/'.cache'/f'repro-{uuid.uuid4().hex}.duckdb'
    assert not database.exists()
    build(database=database)
    actual={k:digest(ROOT/f'data/processed/{k}.csv') for k in expected}
    assert actual==expected,'A fresh database produced different mart exports.'
    run()
    result={'status':'PASS','fresh_database':True,'mart_exports_identical':len(actual),'sha256':actual,
            'note':'New empty DuckDB database, same pinned raw files; byte-identical ordered CSV marts.'}
    (ROOT/'reports/validation/reproducibility.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: all ordered mart exports are byte-identical after a fresh database build.')
