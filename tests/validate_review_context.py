"""Reconcile review-band tooltip calculations, including a five-star hover context."""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if not __debug__:raise RuntimeError('Validation must run without Python -O')

def main():
    groups=defaultdict(lambda:{'eligible':0,'post':0,'low':0})
    with (ROOT/'data/processed/fact_order.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            if r['core_period']=='1' and r['delivery_eligible']=='1':
                g=groups[r['delay_band']];g['eligible']+=1
                if r['post_delivery_review']=='1' and r['review_score']:
                    g['post']+=1;g['low']+=int(r['review_score'])<=2
    observed=json.loads((ROOT/'reports/powerbi/model_review_context.json').read_text(encoding='utf-8-sig'))['rows']
    assert len(observed)==len(groups)==4
    seen=set()
    for row in observed:
        band=row['Order[Delay Band]'];assert band not in seen;seen.add(band);g=groups[band]
        for field,value in [('BandReviews',g['post']),('LowRate',g['low']/g['post']),('Coverage',g['post']/g['eligible'])]:
            assert math.isclose(row[f'[{field}]'],value,rel_tol=1e-10,abs_tol=1e-10),(band,field)
            assert math.isclose(row[f'[Score5{field}]'],value,rel_tol=1e-10,abs_tol=1e-10),(band,'score hover',field)
    evidence={'status':'PASS','bands':4,'contexts':['whole band','score=5 segment'],
              'note':'Expected values calculated from independently reconciled order CSV; score hover must not change band-level low-rating share or coverage.'}
    (ROOT/'reports/powerbi/review_context_validation.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':main()
