"""Validate PBIP/PBIR JSON against Microsoft's published, versioned schemas.

This does not validate visual rendering or DAX; Desktop checks are separate.
"""
import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.cache/schema'

def retrieve(uri):
    if urlparse(uri).hostname!='developer.microsoft.com':raise ValueError(f'Unexpected schema host: {uri}')
    CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE/(hashlib.sha256(uri.encode()).hexdigest()+'.json')
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(uri,timeout=30).read())
    return Resource.from_contents(json.loads(path.read_text()),default_specification=DRAFT7)

def main():
    registry=Registry(retrieve=retrieve)
    count=0;failures=[]
    for path in sorted((ROOT/'powerbi').rglob('*')):
        if path.suffix not in ['.json','.pbip','.pbir','.pbism'] or '.pbi' in path.parts:continue
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        uri=data.get('$schema') if isinstance(data,dict) else None
        if not uri:continue
        schema=retrieve(uri).contents
        validator=jsonschema.validators.validator_for(schema)(schema,registry=registry)
        for error in validator.iter_errors(data):
            failures.append({'file':str(path.relative_to(ROOT)),'path':list(error.absolute_path),'message':error.message[:400]})
        count+=1
    if not count:failures.append({'message':'No schema-bearing report files found'})
    result={'files_checked':count,'status':'FAIL' if failures else 'PASS','errors':failures}
    out=ROOT/'reports/validation/report_schema.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    if failures:raise ValueError('Microsoft report-schema validation failed')

if __name__=='__main__':main()
