"""Independent reconciliation using Python's CSV, Decimal and datetime libraries.

This validator does not import DuckDB or reuse the transformation SQL.
"""
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = Decimal
if not __debug__:raise RuntimeError('Validation must run without Python -O; assertions are required.')

def load(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def run():
    raw = ROOT/'data/raw'
    customers = {r['customer_id']:r for r in load(raw/'olist_customers_dataset.csv')}
    items = defaultdict(lambda:[D(0),D(0),0])
    for r in load(raw/'olist_order_items_dataset.csv'):
        a=items[r['order_id']]; a[0]+=D(r['price']); a[1]+=D(r['freight_value']); a[2]+=1
    payments=defaultdict(lambda:D(0))
    for r in load(raw/'olist_order_payments_dataset.csv'):
        payments[r['order_id']]+=D(r['payment_value'])
    reviews={}
    for r in load(raw/'olist_order_reviews_dataset.csv'):
        key=(r['review_answer_timestamp'],r['review_creation_date'],r['review_id'])
        if r['order_id'] not in reviews or key>reviews[r['order_id']][0]:
            reviews[r['order_id']]=(key,int(r['review_score']))
    expected={}; groups=defaultdict(lambda:{'orders':0,'eligible':0,'late':0,'merchandise_brl':D(0),'freight_brl':D(0)})
    scopes={s:{'orders':0,'eligible':0,'late':0,'delivered':0,'days':[],'scores':[],
               'delivered_merchandise_brl':D(0),'delivered_freight_brl':D(0)} for s in ['all','core']}
    for r in load(raw/'olist_orders_dataset.csv'):
        oid=r['order_id']; purchase=datetime.fromisoformat(r['order_purchase_timestamp'])
        delivered=datetime.fromisoformat(r['order_delivered_customer_date']) if r['order_delivered_customer_date'] else None
        promise=datetime.fromisoformat(r['order_estimated_delivery_date']) if r['order_estimated_delivery_date'] else None
        eligible=int(r['order_status']=='delivered' and delivered is not None and promise is not None and delivered>=purchase)
        late=int(delivered.date()>promise.date()) if eligible else None
        days=(delivered-purchase).total_seconds()/86400 if eligible else None
        core=int(datetime(2017,1,1)<=purchase<datetime(2018,9,1))
        score=reviews[oid][1] if oid in reviews else None
        price,freight,itemcount=items[oid]
        state=customers[r['customer_id']]['customer_state']
        answered=datetime.fromisoformat(reviews[oid][0][0]) if oid in reviews else None
        post=int(answered is not None and delivered is not None and answered>=delivered)
        expected[oid]={'eligible':eligible,'late':late,'days':days,'score':score,'answered':answered,'post':post,'price':price,'freight':freight,'itemcount':itemcount,'core':core}
        g=groups[(purchase.strftime('%Y-%m'),state)]
        g['orders']+=1; g['eligible']+=eligible; g['late']+=late or 0;g['merchandise_brl']+=price;g['freight_brl']+=freight
        for name in (['all','core'] if core else ['all']):
            s=scopes[name];s['orders']+=1;s['eligible']+=eligible;s['late']+=late or 0
            if days is not None:s['days'].append(days)
            if score is not None:s['scores'].append(score)
            if r['order_status']=='delivered':
                s['delivered']+=1;s['delivered_merchandise_brl']+=price;s['delivered_freight_brl']+=freight
    checked=0
    exports=load(ROOT/'data/processed/fact_order.csv')
    assert len(exports)==len(expected)==99441
    for r in exports:
        e=expected.pop(r['order_id'])  # Duplicate or unknown exported ID fails immediately.
        assert int(r['delivery_eligible'])==e['eligible']
        assert (int(r['is_late']) if r['is_late'] else None)==e['late']
        assert (int(r['review_score']) if r['review_score'] else None)==e['score']
        assert (datetime.fromisoformat(r['review_answered_at']) if r['review_answered_at'] else None)==e['answered']
        assert int(r['post_delivery_review'])==e['post']
        assert int(r['core_period'])==e['core']
        assert int(r['item_count'])==e['itemcount']
        for field,key in [('merchandise_brl','price'),('freight_brl','freight')]:
            if e['itemcount']==0:assert r[field]=='', (r['order_id'],'missing amount must stay null')
            assert D(r[field] or '0')==e[key], (r['order_id'],field)
        if e['days'] is not None:assert math.isclose(float(r['delivery_days']),e['days'],abs_tol=1e-10)
        else:assert r['delivery_days']=='','Ineligible orders must have blank duration'
        if r['order_id'] in payments:assert D(r['payment_brl'])==payments[r['order_id']]
        else:assert r['payment_brl']==''
        checked+=1
    assert not expected
    independent={}
    sql=json.loads((ROOT/'reports/validation/sql_baselines.json').read_text())
    for name,s in scopes.items():
        values={k:v for k,v in s.items() if k not in ['days','scores']}
        values.update(median_days=statistics.median(s['days']),p90_days=statistics.quantiles(s['days'],n=10,method='inclusive')[8],
                      average_review=statistics.mean(s['scores']),reviewed=len(s['scores']),low_reviews=sum(x<=2 for x in s['scores']))
        for k,value in values.items():
            other=sql[name][k]
            if isinstance(value,D):assert value==D(other),(name,k,value,other)
            elif isinstance(value,float):assert math.isclose(value,float(other),rel_tol=1e-12,abs_tol=1e-10),(name,k,value,other)
            else:assert value==other,(name,k,value,other)
        independent[name]=values
    sql_slices=json.loads((ROOT/'reports/validation/sql_month_state_slices.json').read_text())
    assert len(sql_slices)==len(groups)
    for row in sql_slices:
        g=groups[(row['month_label'],row['customer_state'])]
        for key,value in g.items():
            # Empty SQL sums stay null in the mart; an empty independent Decimal sum is zero.
            assert value==(D(row[key] or '0') if isinstance(value,D) else row[key]),(row['month_label'],row['customer_state'],key)
    result={'status':'PASS','orders_reconciled_individually':checked,'month_state_slices_reconciled':len(groups),
            'method':'Independent stdlib CSV + Decimal + datetime; no DuckDB or transformation SQL reused',
            'baselines':independent}
    (ROOT/'reports/validation/independent_validation.json').write_text(json.dumps(result,indent=2,default=str)+'\n',encoding='utf-8')
    print(f'PASS: {checked:,} individual orders and {len(groups)} month/state slices reconciled independently.')

if __name__=='__main__':run()
