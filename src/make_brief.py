"""Create an evidence-based two-page management brief from checked query results."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

ROOT=Path(__file__).resolve().parents[1]
INK='#142E42';TEAL='#147D78';MUTED='#607582';PALE='#F1F5F7';ORANGE='#D56B42';MINT='#76D9BA'
W,H=A4;LEFT=42;RIGHT=W-42;WIDTH=RIGHT-LEFT

def read(name):return json.loads((ROOT/'reports/analysis'/name).read_text())
def paragraph(c,value,x,y,width=WIDTH,size=10,color=INK,bold=False,leading=None):
    style=ParagraphStyle('brief',fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,
                         leading=leading or size*1.45,textColor=HexColor(color),spaceAfter=0)
    p=Paragraph(value,style);_,height=p.wrap(width,H)
    assert y-height>36,('Text would overflow page',value[:60],y,height)
    p.drawOn(c,x,y-height)
    return y-height

def header(c,title,subtitle,page):
    c.setFillColor(HexColor(INK));c.rect(0,H-132,W,132,fill=1,stroke=0)
    paragraph(c,'COMMERCE INTELLIGENCE  /  OLIST',LEFT,H-28,size=9,color=MINT,bold=True)
    paragraph(c,title,LEFT,H-51,size=24 if len(title)>25 else 27,color='#FFFFFF',bold=True,leading=31)
    paragraph(c,subtitle,LEFT,H-96,size=9,color='#D8E3E9')
    c.setFillColor(HexColor(MUTED));c.setFont('Helvetica',8)
    c.drawString(LEFT,24,'Educational historical analysis | Olist via Kaggle | CC BY-NC-SA 4.0')
    c.drawRightString(RIGHT,24,f'{page} / 2')

def finding(c,number,title,body,y):
    c.setFillColor(HexColor(TEAL));c.roundRect(LEFT,y-22,25,25,5,fill=1,stroke=0)
    c.setFillColor(white);c.setFont('Helvetica-Bold',10);c.drawCentredString(LEFT+12.5,y-13,number)
    paragraph(c,title,LEFT+38,y+1,WIDTH-38,size=13,bold=True)
    bottom=paragraph(c,body,LEFT+38,y-25,WIDTH-38,size=10)
    c.setStrokeColor(HexColor('#DDE5E9'));c.line(LEFT,bottom-17,RIGHT,bottom-17)
    return bottom-41

def main():
    validation=json.loads((ROOT/'reports/validation/independent_validation.json').read_text())
    assert validation['status']=='PASS'
    core=validation['baselines']['core'];months=read('01_monthly_performance.json');states=read('02_state_priorities.json')
    reviews=read('03_review_association.json');stages=read('06_timing_and_coverage.json')[0]
    audit=read('independent_cohort_audit.json');rest=audit['populations']['rest']
    worst=min(months,key=lambda r:r['on_time_rate'])
    state={r['customer_state']:r for r in states};rj=state['RJ'];sp=state['SP']
    late=next(r for r in reviews if r['review_timing']=='Answered after delivery' and r['is_late']==1)
    ontime=next(r for r in reviews if r['review_timing']=='Answered after delivery' and r['is_late']==0)
    ontime_rate=1-core['late']/core['eligible']
    output=ROOT/'output/pdf/management_summary.pdf';output.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(output),pagesize=A4)
    c.setTitle('Commerce Intelligence - The promise gap')
    c.setAuthor('Commerce Intelligence portfolio project')
    header(c,'The promise gap','Management brief | Purchase cohorts: January 2017-August 2018 | 15 October 2026',1)
    card_width=(WIDTH-20)/3
    for i,(value,label) in enumerate([(f"{core['eligible']:,}",'Eligible delivered orders'),(f'{ontime_rate:.1%}','On-time delivery'),(f"{core['median_days']:.1f} days",'Median delivery time')]):
        x=LEFT+i*(card_width+10);y=H-229
        c.setFillColor(HexColor(PALE));c.roundRect(x,y,card_width,73,8,fill=1,stroke=0)
        paragraph(c,label,x+12,y+60,card_width-24,size=8,color=MUTED)
        paragraph(c,value,x+12,y+41,card_width-24,size=24,color=TEAL,bold=True)
    y=H-258
    y=finding(c,'01','The March 2018 cohort needs investigation',
        f"March 2018 had <b>{worst['on_time_rate']:.1%}</b> on-time delivery versus <b>{rest['on_time_rate']:.1%}</b> in the other core-period months: a <b>{-audit['march_minus_rest_on_time_difference']*100:.1f} percentage-point gap</b>. "
        f"It contains {worst['late']:,} late orders from {worst['eligible']:,} eligible deliveries. The gap remains after destination-state standardization; eligibility is about 97.1% in both groups. This is a meaningful purchase-cohort signal, not a diagnosed cause or causal effect.",y)
    y=finding(c,'02','Separate a rate problem from a volume problem',
        f"<b>Rio de Janeiro (RJ)</b> had {rj['late']:,} late orders and a <b>{rj['late_rate']:.1%}</b> late rate ({rj['eligible']:,} eligible). "
        f"<b>Sao Paulo (SP)</b> had more late orders ({sp['late']:,}) but a lower {sp['late_rate']:.1%} rate ({sp['eligible']:,} eligible). "
        f"Together they account for {(rj['late']+sp['late'])/core['late']:.1%} of late orders; that concentration partly reflects volume.",y)
    y=finding(c,'03','Review timing changes the interpretation',
        f"Among selected reviews answered <b>after delivery</b>, low ratings (1-2 stars) were <b>{late['low_rating_rate']:.1%} for late orders</b> "
        f"(n={late['reviewed_orders']:,}) versus <b>{ontime['low_rating_rate']:.1%} for on-time orders</b> (n={ontime['reviewed_orders']:,}). "
        f"Post-delivery response coverage is only <b>{audit['review_selection']['late']['post_coverage_of_eligible']:.1%} of late orders</b> versus <b>{audit['review_selection']['on_time']['post_coverage_of_eligible']:.1%} of on-time orders</b>. This unequal selection prevents interpreting the rating gap as the effect of lateness.",y)
    paragraph(c,'Decision: investigate destination/cohort bottlenecks first, then test a narrow operational intervention. Do not infer savings or carrier fault from this dataset.',LEFT,y,WIDTH,size=10,bold=True)
    paragraph(c,'Evidence: reports/analysis/independent_cohort_audit.json and sql/analysis/. March-minus-other-month rate gap: -13.1 pp; descriptive 95% Wilson-Newcombe interval -14.1 to -12.2 pp. Month selected after inspection; clustering, selection and causal uncertainty remain.',LEFT,83,WIDTH,size=8,color=MUTED)
    c.showPage()
    header(c,'A focused improvement agenda','Proposed pilot actions, ownership and measures - not interventions already tested',2)
    y=H-163
    y=finding(c,'01','Operations: investigate RJ lanes and peak cohorts',
        'Review event quality and promise-setting for RJ, stratified by purchase month and category. Compare the weak March cohort with nearby cohorts before choosing a pilot. '
        '<b>Measure:</b> calendar-date on-time rate and P90 elapsed days. <b>Guardrails:</b> cancellations, volume and promised lead time; do not improve the rate simply by extending promises.',y)
    y=finding(c,'02','Seller operations: audit a bounded handoff queue',
        'Start with the ranked single-seller queue and inspect the underlying orders before assigning responsibility. Anonymous Seller 7C67E144 has 963 eligible orders, 89 late outcomes and an 11.0-day median valid handoff stage; product and destination mix could explain part of the pattern. '
        '<b>Measure:</b> valid handoff time plus end-to-end on-time rate, using a comparable control group.',y)
    y=finding(c,'03','Customer experience: retain both survey clocks',
        'Report pre-delivery and post-delivery feedback separately. Test proactive communication on a defined at-risk cohort, with a comparison group and a pre-agreed measurement window. '
        '<b>Measure:</b> post-delivery low-rating share and its response coverage. Survey timing and response selection remain part of interpretation.',y)
    y=paragraph(c,'Methods and limits',LEFT,y,WIDTH,size=12,bold=True)-10
    paragraph(c,
        f"The source has 99,441 orders; the core period has {core['orders']:,}. Delivery KPIs use {core['eligible']:,} delivered orders with valid required dates. "
        'Delivery on the promised calendar date is on time. Reviews use one latest response per order, chosen deterministically. '
        f"The single-seller diagnostic covers {stages['single_seller_eligible']/core['eligible']:.1%} of eligible deliveries. "
        'Stage metrics exclude their own chronology exceptions; their medians are not additive. '
        'Merchandise values exclude freight and are not adjusted for refunds; margin is unavailable. Exposure is not lost revenue. Carrier identity, actual logistics costs and causal intervention evidence are absent. '
        'SQL, independent Python checks, real Desktop DAX reconciliation, exception ledgers and source hashes accompany the project.',LEFT,y,WIDTH,size=9,color=MUTED,leading=13)
    c.save()
    markdown=f'''# Commerce Intelligence - Management summary

Core purchase cohorts: January 2017-August 2018. Historical Olist data; not current operating performance.

## Findings

- **Promise adherence:** {ontime_rate:.1%}; {core['late']:,} late orders from {core['eligible']:,} eligible deliveries. Median {core['median_days']:.1f} days; P90 {core['p90_days']:.1f} days.
- **Peak cohort:** March 2018 had {worst['on_time_rate']:.1%} on-time delivery and {worst['late']:,} late orders from {worst['eligible']:,} eligible deliveries, versus {rest['on_time_rate']:.1%} in other core months (a {-audit['march_minus_rest_on_time_difference']*100:.1f} percentage-point gap). State-standardized rates remain {audit['state_standardization']['rates']['march']:.1%} versus {audit['state_standardization']['rates']['rest']:.1%}. Eligibility is about 97.1% in both groups. The decline is materially descriptive; its cause is unknown. The month was selected after inspection, and order independence is not guaranteed; the descriptive 95% difference interval (-14.1 to -12.2 pp) is not a causal or preregistered test.
- **Geography:** RJ had {rj['late_rate']:.1%} late delivery versus SP's {sp['late_rate']:.1%}. SP had the larger late count ({sp['late']:,} versus {rj['late']:,}). Combined, {(rj['late']+sp['late'])/core['late']:.1%} of late orders; volume matters.
- **Review timing:** post-delivery low-rating share was {late['low_rating_rate']:.1%} for late orders (n={late['reviewed_orders']:,}) versus {ontime['low_rating_rate']:.1%} for on-time orders (n={ontime['reviewed_orders']:,}). Coverage is only 29.2% of late versus 99.3% of on-time eligible orders. This highly selected sample cannot estimate a delivery effect. The source describes surveys sent upon receipt or when the estimated date is due, so survey timing is tied to the delivery process. Pre-delivery responses must remain separate.
- **Operational stages:** median valid handoff {stages['median_handoff_days']:.2f} days and transit {stages['median_transit_days']:.2f} days. These stage medians are not additive and use different valid samples.

## Recommended pilots

1. Operations: diagnose RJ/cohort promise gaps before a narrow lane or communication pilot. Measure on-time %, P90, cancellations and promise length against a comparable group.
2. Seller operations: audit the single-seller queue before assigning fault. Seller 7C67E144 warrants inspection (963 eligible; 89 late; 11.0-day valid handoff median), controlling for product/destination mix.
3. Customer experience: report both survey clocks and test proactive communication with a comparison group. Track post-delivery low ratings and review coverage.

No carrier, cost, margin, refund or experimentally verified savings claim is supported. Findings link to `sql/analysis/` and inspectable results in `reports/analysis/`. Source: [Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
'''
    (ROOT/'reports/management_summary.md').write_text(markdown,encoding='utf-8')
    print(output)

if __name__=='__main__':main()
