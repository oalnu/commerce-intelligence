"""Independent raw-CSV audit of delivery cohorts and review selection sensitivity.

No DuckDB, mart data or transformation SQL is used for the estimates below.
Intervals describe binomial sampling variation, not uncertainty about missing
outcomes, dependence between orders, survey selection or operational causes.
"""
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def rows(name):
    with (ROOT/'data/raw'/name).open(encoding='utf-8-sig',newline='') as f:
        yield from csv.DictReader(f)

def wilson(k,n):
    if not n:return None
    z=1.96;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [mid-half,mid+half]

def summarize(group):
    eligible=[r for r in group if r['eligible']]
    on=sum(not r['late'] for r in eligible)
    return {'orders':len(group),'status_counts':dict(sorted(Counter(r['status'] for r in group).items())),
            'eligible':len(eligible),'on_time':on,'late':len(eligible)-on,
            'on_time_rate':on/len(eligible),'on_time_wilson_95':wilson(on,len(eligible)),
            'eligible_share':len(eligible)/len(group),
            'observed_on_time_share_all_orders':on/len(group),
            'median_promised_lead_calendar_days':median([r['promise_days'] for r in eligible])}

def median(values):
    v=sorted(values);n=len(v)
    return v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2

def main():
    states={r['customer_id']:r['customer_state'] for r in rows('olist_customers_dataset.csv')}
    reviews={}
    for r in rows('olist_order_reviews_dataset.csv'):
        key=(r['review_answer_timestamp'],r['review_creation_date'],r['review_id'])
        if r['order_id'] not in reviews or key>reviews[r['order_id']][0]:
            reviews[r['order_id']]=(key,int(r['review_score']))
    records=[];timestamp_late=0;calendar_late=0
    review_groups=defaultdict(lambda:Counter(eligible=0,reviewed=0,post=0,post_low=0,pre=0,pre_low=0))
    for r in rows('olist_orders_dataset.csv'):
        buy=datetime.fromisoformat(r['order_purchase_timestamp'])
        promise=datetime.fromisoformat(r['order_estimated_delivery_date']) if r['order_estimated_delivery_date'] else None
        actual=datetime.fromisoformat(r['order_delivered_customer_date']) if r['order_delivered_customer_date'] else None
        valid=r['order_status']=='delivered' and actual is not None and promise is not None and actual>=buy
        late=actual.date()>promise.date() if valid else None
        if valid:timestamp_late+=actual>promise;calendar_late+=late
        if not datetime(2017,1,1)<=buy<datetime(2018,9,1):continue
        records.append({'month':buy.strftime('%Y-%m'),'state':states[r['customer_id']],
                        'status':r['order_status'],'eligible':valid,'late':late,
                        'promise_days':(promise.date()-buy.date()).days if promise else None})
        if valid:
            g=review_groups['late' if late else 'on_time'];g['eligible']+=1
            selected=reviews.get(r['order_id'])
            if selected:
                g['reviewed']+=1
                when='post' if datetime.fromisoformat(selected[0][0])>=actual else 'pre'
                g[when]+=1;g[when+'_low']+=selected[1]<=2
    march=[r for r in records if r['month']=='2018-03']
    rest=[r for r in records if r['month']!='2018-03']
    summary={name:summarize(group) for name,group in [('core',records),('march',march),('rest',rest)]}
    # Common-state direct standardization: use the pooled eligible state mix.
    by_state=defaultdict(lambda:{'march':[0,0],'rest':[0,0]})
    for r in records:
        if r['eligible']:
            x=by_state[r['state']]['march' if r['month']=='2018-03' else 'rest']
            x[0]+=1;x[1]+=not r['late']
    common={s:g for s,g in by_state.items() if g['march'][0] and g['rest'][0]}
    total=sum(sum(v[0] for v in g.values()) for g in common.values())
    standardized={name:sum(sum(v[0] for v in g.values())/total*g[name][1]/g[name][0] for g in common.values()) for name in ['march','rest']}
    state_rows=[{'state':s,'march_eligible':g['march'][0],'rest_eligible':g['rest'][0],
                 'march_on_time_rate':g['march'][1]/g['march'][0],
                 'rest_on_time_rate':g['rest'][1]/g['rest'][0]} for s,g in sorted(common.items())]
    # Disjoint comparison; Newcombe interval from each Wilson interval.
    a=summary['march'];b=summary['rest'];delta=a['on_time_rate']-b['on_time_rate']
    lo=delta-math.sqrt((a['on_time_rate']-a['on_time_wilson_95'][0])**2+(b['on_time_wilson_95'][1]-b['on_time_rate'])**2)
    hi=delta+math.sqrt((a['on_time_wilson_95'][1]-a['on_time_rate'])**2+(b['on_time_rate']-b['on_time_wilson_95'][0])**2)
    timing={}
    for name,g in review_groups.items():
        timing[name]={**g,'post_coverage_of_eligible':g['post']/g['eligible'],
                      'post_low_rate':g['post_low']/g['post'],'pre_low_rate':g['pre_low']/g['pre']}
    result={'checked_utc':datetime.now(timezone.utc).isoformat(),'method':'Independent raw CSV + datetime; no SQL/mart reuse',
            'populations':summary,'march_minus_rest_on_time_difference':delta,
            'difference_newcombe_wilson_95':[lo,hi],
            'state_standardization':{'common_states':len(common),'eligible_coverage':total/summary['core']['eligible'],
                                    'rates':standardized,'march_minus_rest':standardized['march']-standardized['rest'],'states':state_rows},
            'review_selection':timing,
            'all_source_late_definition_sensitivity':{'calendar_date':calendar_late,'full_timestamp':timestamp_late},
            'limits':['Purchase cohort, not delivery month. March chosen after inspecting all months; interval is descriptive, not a preregistered significance test.',
                      'Orders are not guaranteed independent; intervals do not address clustering, censoring or dataset selection.',
                      'State standardization addresses observed destination mix only, not product/seller mix or causality.',
                      'Observed on-time share of all orders treats noneligible outcomes as not demonstrated on time; it is not the delivery-only KPI.',
                      'Post-delivery survey coverage differs sharply by lateness; the rating gap cannot identify a delivery effect.']}
    out=ROOT/'reports/analysis/independent_cohort_audit.json'
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='state_standardization'},indent=2))
    print('State-standardized rates:',standardized)

if __name__=='__main__':main()
