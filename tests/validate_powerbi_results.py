"""Reconcile real Desktop DAX output with independently checked SQL/CSV baselines."""
import csv
import json
import math
import re
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'reports/powerbi'
if not __debug__:raise RuntimeError('Validation must run without Python -O; assertions are required.')

def read(name):return json.loads((E/name).read_text(encoding='utf-8-sig'))
def close(actual,expected):
    if expected is None:assert actual is None
    elif isinstance(expected,str):
        assert actual is not None,(actual,expected)
        assert abs(Decimal(str(actual))-Decimal(expected))<=Decimal('0.01'),(actual,expected)
    elif isinstance(expected,float):assert math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-9),(actual,expected)
    else:assert actual==expected,(actual,expected)

def main():
    relationships=read('model_relationships.json')['rows']
    source=(ROOT/'powerbi/CommerceIntelligence.SemanticModel/definition/relationships.tmdl').read_text()
    expected_relationships=set(re.findall(r'^relationship ([\w-]+)',source,re.M))
    assert len(relationships)==len(expected_relationships)==7
    assert {r['Name'] for r in relationships}==expected_relationships
    for r in relationships:
        assert r['IsActive'] is True and r['FromCardinality']==2 and r['ToCardinality']==1 and r['CrossFilteringBehavior']==1,r
    table_rows=read('model_tables.json')['rows'];assert len(table_rows)==1,'Expected one table-count record'
    tables=table_rows[0]
    manifest=json.loads((ROOT/'reports/validation/build_manifest.json').read_text())
    for table,details in manifest['exports'].items():close(tables['['+table+']'],details['rows'])
    sql=json.loads((ROOT/'reports/validation/sql_baselines.json').read_text())
    mapping={'Orders':'orders','Eligible':'eligible','Late':'late','MedianDays':'median_days','P90Days':'p90_days',
             'AverageReview':'average_review','Reviewed':'reviewed','LowReviews':'low_reviews',
             'DeliveredMerchandise':'delivered_merchandise_brl','DeliveredFreight':'delivered_freight_brl'}
    baseline_rows=read('model_baselines.json')['rows']
    assert len(baseline_rows)==2 and {r['[Scope]'].lower() for r in baseline_rows}=={'all','core'},'Missing or duplicate baseline scopes'
    for row in baseline_rows:
        expected=sql[row['[Scope]'].lower()]
        for dax,key in mapping.items():close(row['['+dax+']'],expected[key])
        close(row['[OnTime]'],(expected['eligible']-expected['late'])/expected['eligible'])
    slices=json.loads((ROOT/'reports/validation/sql_month_state_slices.json').read_text())
    expected={(r['month_label'],r['customer_state']):r for r in slices}
    actual=read('model_month_state.json')['rows'];assert len(actual)==len(expected)
    for row in actual:
        source=expected.pop((row['Date[Month Label]'],row['State[State]']))
        for key,skey in [('OrderCount','orders'),('EligibleCount','eligible'),('LateCount','late'),('Merchandise','merchandise_brl'),('Freight','freight_brl')]:
            value=source[skey]
            # Empty sums may be BLANK; don't turn missing order-level values into zero.
            close(row['['+key+']'],value)
    assert not expected
    diagnostic_rows=read('model_diagnostics.json')['rows'];assert len(diagnostic_rows)==1,'Expected one diagnostic record'
    diagnostics=diagnostic_rows[0]
    coverage=json.loads((ROOT/'reports/analysis/06_timing_and_coverage.json').read_text())[0]
    for name,key in [('SingleSellerEligible','single_seller_eligible'),('SingleCategoryEligible','single_category_eligible'),('HandoffMedian','median_handoff_days'),('TransitMedian','median_transit_days'),('PostDeliveryReviewed','post_delivery_reviewed')]:
        close(diagnostics['['+name+']'],coverage[key])
    with (ROOT/'data/processed/fact_order.csv').open(encoding='utf-8',newline='') as f:
        late_value=sum((Decimal(r['merchandise_brl']) for r in csv.DictReader(f) if r['core_period']=='1' and r['is_late']=='1' and r['merchandise_brl']),Decimal(0))
    close(diagnostics['[LateExposureBRL]'],str(late_value))
    close(diagnostics['[ExcludedDelivered]'],8)
    result={'status':'PASS','table_row_counts':len(tables),'active_many_to_one_single_direction_relationships':7,'all_and_core_kpis':True,'month_state_slices':len(actual),'diagnostic_measures':True,
            'money_tolerance_brl':'0.01','numeric_tolerance':'relative 1e-10 / absolute 1e-9',
            'note':'Actual Desktop ADOMD results; semantic validation does not replace UI interaction checks.'}
    (E/'validation_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
