"""Generate the local Power BI project from validated SQL marts and a Desktop seed.

Generation is not validation: open, refresh and reconcile the result in Desktop.
"""
from __future__ import annotations
import copy
import json
import shutil
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'powerbi'
PROJECT='CommerceIntelligence'
REPORT=DEST/f'{PROJECT}.Report'
MODEL=DEST/f'{PROJECT}.SemanticModel'
INK='#142E42';TEAL='#147D78';MINT='#76D9BA';ORANGE='#D56B42';MUTED='#607582';BG='#F1F5F7'
ZCOUNTS={}
TABLES={'fact_order':'Order','fact_item':'Item','dim_date':'Date','dim_customer_state':'State',
        'dim_seller':'Seller','dim_category':'Category','dim_product':'Product','dim_status':'Status','dim_stage':'Stage'}
SPECIAL={'order_id':'Order ID','date_key':'Date Key','customer_unique_id':'Customer Person ID','merchandise_brl':'Merchandise BRL',
         'freight_brl':'Freight BRL','payment_brl':'Payment BRL','price_brl':'Price BRL','product_id':'Product ID',
         'seller_id':'Seller ID','is_late':'Is Late','review_score':'Review Score','core_period':'Core Period'}

def label(s):return SPECIAL.get(s,s.replace('_',' ').title())
def uid(name):return str(uuid.uuid5(uuid.NAMESPACE_URL,'commerce-intelligence/'+name))
def short(name):return uuid.uuid5(uuid.NAMESPACE_URL,'commerce-intelligence/'+name).hex[:20]
def q(s):return "'"+s.replace("'","''")+"'"
def m_quote(s):return '"'+s.replace('"','""')+'"'
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def text(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value,encoding='utf-8')

# Explicit measures only. Period and geography arrive through dimension filters.
MEASURES={
 'Orders':('COUNTROWS(\'Order\')','#,0','All source-status orders in the current purchase-date and geography context.'),
 'Eligible Delivered':('SUM(\'Order\'[Delivery Eligible])','#,0','Delivered orders with valid actual/promise dates and nonnegative total delivery duration.'),
 'Late Orders':('COALESCE(SUM(\'Order\'[Is Late]),0)','#,0','Actual delivery calendar date is after the estimated calendar date; eligible delivered orders only.'),
 'On-time Delivery':('DIVIDE([Eligible Delivered]-[Late Orders],[Eligible Delivered])','0.0%','On-time eligible deliveries divided by eligible delivered orders. Zero denominator returns blank.'),
 'Late Rate':('DIVIDE([Late Orders],[Eligible Delivered])','0.0%','Late orders divided by eligible delivered orders.'),
 'Median Delivery Days':('MEDIAN(\'Order\'[Delivery Days])','0.0','Median elapsed purchase-to-delivery days; invalid outcomes are blank.'),
 'P90 Delivery Days':('PERCENTILEX.INC(FILTER(\'Order\',\'Order\'[Delivery Eligible]=1),\'Order\'[Delivery Days],0.9)','0.0','90th percentile elapsed days among eligible delivered orders; blanks excluded.'),
 'Average Review':('AVERAGE(\'Order\'[Review Score])','0.00','One latest selected valid review per order; reviewed orders only, including all statuses.'),
 'Reviewed Orders':('COUNT(\'Order\'[Review Score])','#,0','Orders with a selected review score.'),
 'Review Coverage':('DIVIDE([Reviewed Orders],[Orders])','0.0%','Selected-review coverage across all selected orders.'),
 'Low Reviews':('CALCULATE([Reviewed Orders],KEEPFILTERS(\'Order\'[Review Score]<=2))','#,0','Selected order reviews scored 1 or 2.'),
 'Low Rating Rate':('DIVIDE([Low Reviews],[Reviewed Orders])','0.0%','Low selected reviews divided by reviewed orders.'),
 'Post-delivery Reviews':('CALCULATE([Reviewed Orders],\'Order\'[Delivery Eligible]=1,\'Order\'[Post Delivery Review]=1)','#,0','Selected reviews answered on/after delivery, within eligible delivered orders.'),
 'Post-delivery Low Rating':('DIVIDE(CALCULATE([Low Reviews],REMOVEFILTERS(\'Order\'[Review Score]),\'Order\'[Delivery Eligible]=1,\'Order\'[Post Delivery Review]=1),CALCULATE([Post-delivery Reviews],REMOVEFILTERS(\'Order\'[Review Score])))','0.0%','Low-rating share of the full delay-band post-delivery sample, unaffected by hovered score segment. Descriptive, not causal.'),
 'Post-delivery Band Reviews':('CALCULATE([Post-delivery Reviews],REMOVEFILTERS(\'Order\'[Review Score]))','#,0','Full delay-band post-delivery sample size; ignores the hovered score segment.'),
 'Post-delivery Coverage':('DIVIDE([Post-delivery Band Reviews],CALCULATE([Eligible Delivered],REMOVEFILTERS(\'Order\'[Review Score])))','0.0%','Post-delivery selected responses divided by eligible orders in the delay band; ignores score segment.'),
 'Review Timing Note':('VAR LateCoverage = CALCULATE([Post-delivery Coverage],REMOVEFILTERS(\'Order\'[Delay Band],\'Order\'[Review Score]),\'Order\'[Is Late]=1) VAR OnCoverage = CALCULATE([Post-delivery Coverage],REMOVEFILTERS(\'Order\'[Delay Band],\'Order\'[Review Score]),\'Order\'[Is Late]=0) RETURN "Post-delivery coverage: late " & IF(ISBLANK(LateCoverage),"n/a",FORMAT(LateCoverage,"0.0%")) & " | on time " & IF(ISBLANK(OnCoverage),"n/a",FORMAT(OnCoverage,"0.0%")) & " | selected responses; not causal"','','Dynamic coverage warning retains date/state selections; prevents presenting the selected survey sample as representative.'),
 'Delivered Merchandise BRL':('CALCULATE(SUM(\'Order\'[Merchandise BRL]),\'Order\'[Order Status]="delivered")','"R$ "#,0.00','Item prices once per delivered order. Excludes freight; not profit or recognized net revenue.'),
 'Delivered Freight BRL':('CALCULATE(SUM(\'Order\'[Freight BRL]),\'Order\'[Order Status]="delivered")','"R$ "#,0.00','Freight charges on delivered orders; not logistics costs.'),
 'Freight to Merchandise':('DIVIDE([Delivered Freight BRL],[Delivered Merchandise BRL])','0.0%','Ratio of sums over the same delivered-order population.'),
 'Late Order Exposure BRL':('CALCULATE(SUM(\'Order\'[Merchandise BRL]),\'Order\'[Is Late]=1)','"R$ "#,0','Merchandise value of late eligible orders; exposure, not lost revenue.'),
 'Delivery Exclusions':('CALCULATE([Orders],\'Order\'[Order Status]="delivered")-[Eligible Delivered]','#,0','Delivered-status orders excluded because required actual/promise dates or total chronology are invalid.'),
 'State Priority Flag':('IF([Eligible Delivered]>=100 && RANKX(ALLSELECTED(\'State\'[State]),[Late Orders],,DESC,Dense)<=8,1,0)','0','Top eight ranks by late-order count with at least 100 eligible orders.'),
 'Category Eligible':('CALCULATE([Eligible Delivered],\'Order\'[Category Count]=1)','#,0','Single-category eligible delivered orders; other categories are not attributed to a dominant product.'),
 'Category Late Orders':('CALCULATE([Late Orders],\'Order\'[Category Count]=1)','#,0','Late single-category orders.'),
 'Category Late Rate':('DIVIDE([Category Late Orders],[Category Eligible])','0.0%','Late rate on single-category orders.'),
 'Category Priority Flag':('IF([Category Eligible]>=100 && RANKX(ALLSELECTED(\'Category\'[Category]),[Category Late Orders],,DESC,Dense)<=8,1,0)','0','Top eight late-count ranks among category segments, with at least 100 eligible orders.'),
 'Seller Eligible':('CALCULATE([Eligible Delivered],\'Order\'[Seller Count]=1)','#,0','Single-seller eligible orders only; no attribution of a multi-seller delay to one seller.'),
 'Seller Late Orders':('CALCULATE([Late Orders],\'Order\'[Seller Count]=1)','#,0','Late single-seller eligible orders.'),
 'Seller Late Rate':('DIVIDE([Seller Late Orders],[Seller Eligible])','0.0%','Late rate among single-seller eligible orders.'),
 'Seller Priority Flag':('IF([Seller Eligible]>=100 && RANKX(ALLSELECTED(\'Seller\'[Seller]),[Seller Late Orders],,DESC,Dense)<=8,1,0)','0','Top eight late-count ranks among sellers with at least 100 eligible orders.'),
 'Seller Coverage':('DIVIDE([Seller Eligible],[Eligible Delivered])','0.0%','Share of eligible orders that can be attributed to a single seller.'),
 'Median Handoff Days':('CALCULATE(MEDIAN(\'Order\'[Handoff Days]),\'Order\'[Delivery Eligible]=1)','0.0','Median approval-to-handoff elapsed days on valid stages; eligible delivered orders.'),
 'Median Transit Days':('CALCULATE(MEDIAN(\'Order\'[Transit Days]),\'Order\'[Delivery Eligible]=1)','0.0','Median carrier-to-customer elapsed days on valid stages; eligible delivered orders.'),
 'Median Stage Days':('SWITCH(SELECTEDVALUE(\'Stage\'[Stage Order]),1,CALCULATE(MEDIAN(\'Order\'[Approval Days]),\'Order\'[Delivery Eligible]=1),2,[Median Handoff Days],3,[Median Transit Days])','0.000','Stage medians use stage-specific valid records and are not additive.'),
 'Valid Stage Orders':('SWITCH(SELECTEDVALUE(\'Stage\'[Stage Order]),1,CALCULATE(COUNT(\'Order\'[Approval Days]),\'Order\'[Delivery Eligible]=1),2,CALCULATE(COUNT(\'Order\'[Handoff Days]),\'Order\'[Delivery Eligible]=1),3,CALCULATE(COUNT(\'Order\'[Transit Days]),\'Order\'[Delivery Eligible]=1))','#,0','Stage-specific valid sample size among eligible delivered orders.'),
}

def make_model(manifest):
    write(MODEL/'definition.pbism',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json','version':'4.2','settings':{}})
    text(MODEL/'definition/database.tmdl','database\n\tcompatibilityLevel: 1606\n')
    text(MODEL/'definition/cultures/en-US.tmdl','cultureInfo en-US\n')
    text(MODEL/'definition/expressions.tmdl','expression DataRoot = '+m_quote(str((ROOT/'data/processed').resolve()).replace('\\','/'))+' meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n\tlineageTag: '+uid('DataRoot')+'\n\tannotation PBI_NavigationStepName = Navigation\n\tannotation PBI_ResultType = Text\n')
    lines=['model Model','\tculture: en-US','\tdefaultPowerBIDataSourceVersion: powerBI_V3','\tsourceQueryCulture: en-US','\tvalueFilterBehavior: independent','\tdataAccessOptions','\t\tlegacyRedirects','\t\treturnErrorValuesAsNull','','annotation __PBI_TimeIntelligenceEnabled = 0','', 'annotation PBI_QueryOrder = '+json.dumps(['DataRoot']+list(TABLES.values())),'']
    for src,table in TABLES.items():
        columns=manifest['exports'][src]['columns']
        body=[f'table {q(table)}',f'\tlineageTag: {uid(table)}','']
        typepairs=[]
        for c in columns:
            col=c['column_name'];friendly=label(col);dtype=c['column_type']
            td='string' if dtype=='VARCHAR' else 'dateTime' if dtype in ['DATE','TIMESTAMP'] else 'decimal' if dtype.startswith('DECIMAL') else 'double' if dtype in ['DOUBLE','FLOAT'] else 'int64'
            mt='type text' if td=='string' else 'type date' if dtype=='DATE' else 'type datetime' if td=='dateTime' else 'Currency.Type' if td=='decimal' else 'type number' if td=='double' else 'Int64.Type'
            body += [f'\tcolumn {q(friendly)}',f'\t\tdataType: {td}',f'\t\tlineageTag: {uid(table+"/"+col)}','\t\tsummarizeBy: none',f'\t\tsourceColumn: {col}']
            if col.endswith('_id') or col.endswith('_key') or col in ['core_period','customer_unique_id','stage_order','delay_band_sort','post_delivery_review','delivery_eligible','seller_count','category_count','is_late']:
                body += ['\t\tisHidden']
            if td=='dateTime':body += ['\t\tformatString: yyyy-MM-dd' if dtype=='DATE' else '\t\tformatString: yyyy-MM-dd HH:mm:ss']
            if col=='delay_band':body += ["\t\tsortByColumn: 'Delay Band Sort'"]
            if table=='Stage' and col=='stage':body += ["\t\tsortByColumn: 'Stage Order'"]
            body += ['']
            typepairs.append('{'+json.dumps(col)+', '+mt+'}')
        if table=='Order':
            for name,(dax,fmt,description) in MEASURES.items():
                body += [f'\t/// {description}',f'\tmeasure {q(name)} = {dax}']
                if fmt:body += [f'\t\tformatString: {fmt}']
                body += [f'\t\tlineageTag: {uid("measure/"+name)}',"\t\tdisplayFolder: KPIs",'']
        m=['let',f'    Source = Csv.Document(File.Contents(DataRoot & "/{src}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),','    Headers = Table.PromoteHeaders(Source,[PromoteAllScalars=true]),',f'    Typed = Table.TransformColumnTypes(Headers, {{{", ".join(typepairs)}}}, "en-US")','in','    Typed']
        body += [f'\tpartition {q(table)} = m','\t\tmode: import','\t\tsource =']+['\t\t\t\t'+line for line in m]+['','\tannotation PBI_ResultType = Table','\tannotation PBI_NavigationStepName = Navigation','']
        text(MODEL/f'definition/tables/{table}.tmdl','\n'.join(body))
        lines += [f'ref table {q(table)}']
    lines += ['','ref expression DataRoot','ref cultureInfo en-US','']
    text(MODEL/'definition/model.tmdl','\n'.join(lines))
    relationships=[('Order','Date Key','Date','Date Key'),('Order','Customer State','State','State Key'),('Order','Seller Key','Seller','Seller Key'),('Order','Category Key','Category','Category Key'),('Order','Order Status','Status','Order Status'),('Item','Order ID','Order','Order ID'),('Item','Product ID','Product','Product ID')]
    text(MODEL/'definition/relationships.tmdl','\n\n'.join(f'relationship {uid(str(r))}\n\tfromColumn: {q(r[0])}.{q(r[1])}\n\ttoColumn: {q(r[2])}.{q(r[3])}\n\tcrossFilteringBehavior: oneDirection' for r in relationships)+'\n')
    write(ROOT/'docs/measure_dictionary.json',{name:{'dax':dax,'format':fmt,'definition':description} for name,(dax,fmt,description) in MEASURES.items()})

def lit(v):
    value='true' if v is True else 'false' if v is False else f'{v}D' if isinstance(v,(int,float)) else q(v)
    return {'expr':{'Literal':{'Value':value}}}
def color(c):return {'solid':{'color':lit(c)}}
def obj(**props):return [{'properties':props}]
def field(table,column=None,measure=None):
    return {('Measure' if measure else 'Column'):{'Expression':{'SourceRef':{'Entity':table}},'Property':measure or column}}
def projection(f):
    e=next(iter(f.values()));entity=e['Expression']['SourceRef']['Entity'];prop=e['Property']
    alias={'Seller Eligible':'Eligible','Seller Late Orders':'Late','Seller Late Rate':'Late %','Median Handoff Days':'Handoff days','Median Stage Days':'Median days','Valid Stage Orders':'Valid orders'}
    return {'field':f,'queryRef':f'{entity}.{prop}','nativeQueryRef':prop,'displayName':alias.get(prop,prop)}
def meas(name):return field('Order',measure=name)
def eqfilter(table,column,value,measure=False):
    typ='Measure' if measure else 'Column'
    return {'name':short('filter/'+table+'/'+column+'/'+str(value)), 'field':field(table,column if not measure else None,column if measure else None),'type':'Advanced' if measure else 'Categorical',
            'filter':{'Version':2,'From':[{'Name':'f','Entity':table,'Type':0}],'Where':[{'Condition':{'Comparison':{'ComparisonKind':0,'Left':{typ:{'Expression':{'SourceRef':{'Source':'f'}},'Property':column}},'Right':{'Literal':{'Value':str(value)+'L'}}}}}]}}

def container(title=None,subtitle=None,bg='white'):
    result={'background':obj(show=lit(bg!='transparent'),color=color('#FFFFFF' if bg=='white' else BG if bg=='transparent' else bg),transparency=lit(0)),
            'border':obj(show=lit(bg=='white'),color=color('#DDE5E9'),radius=lit(10),width=lit(1)),
            'padding':obj(left=lit(18),right=lit(18),top=lit(14),bottom=lit(10)),
            'visualHeader':obj(show=lit(True),showFilterRestatementButton=lit(False),showFocusModeButton=lit(True),showOptionsMenu=lit(True))}
    if title:result['title']=obj(show=lit(True),text=lit(title),fontColor=color(INK),fontSize=lit(14),fontFamily=lit('Segoe UI Semibold'),bold=lit(True),titleWrap=lit(False))
    if subtitle:result['subTitle']=obj(show=lit(True),text=lit(subtitle),fontColor=color(MUTED),fontSize=lit(10),fontFamily=lit('Segoe UI'),titleWrap=lit(False))
    return result

def visual(page,name,kind,pos,roles=None,objects=None,title=None,subtitle=None,filters=None,bg='white',sort=None,sync=None):
    ident=short(page+'/'+name)
    v={'visualType':kind,'visualContainerObjects':container(title,subtitle,bg),'drillFilterOtherVisuals':True}
    if roles:v['query']={'queryState':{role:{'projections':[projection(f) for f in fs]} for role,fs in roles.items()}}
    if objects:v['objects']=objects
    if kind=='textbox':
        v['visualContainerObjects']['padding']=obj(left=lit(0),right=lit(0),top=lit(0),bottom=lit(0))
        v['visualContainerObjects']['visualHeader']=obj(show=lit(False))
    if sort:v.setdefault('query',{})['sortDefinition']={'sort':[{'field':sort[0],'direction':sort[1]}]}
    if sync:v['syncGroup']={'groupName':sync,'fieldChanges':True,'filterChanges':True}
    x,y,w,h=pos
    z=ZCOUNTS.get(page,0);ZCOUNTS[page]=z+1
    data={'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json','name':ident,
          'position':{'x':x,'y':y,'z':z,'width':w,'height':h,'tabOrder':int(y*10+x)},'visual':v}
    if filters:data['filterConfig']={'filters':filters}
    write(REPORT/f'definition/pages/{page}/visuals/{ident}/visual.json',data)
    return ident

def textbox(page,name,pos,runs,bg='transparent'):
    paragraphs=[]
    for value,size,c,bold in runs:
        paragraphs.append({'textRuns':[{'value':value,'textStyle':{'fontFamily':'Segoe UI','fontSize':str(size)+'pt','color':c,'fontWeight':'bold' if bold else 'normal'}}]})
    visual(page,name,'textbox',pos,objects={'general':obj(paragraphs=paragraphs)},bg=bg)

def slicer(page,name,pos,f,sync):
    visual(page,name,'slicer',pos,{'Values':[f]},objects={'data':obj(mode=lit('Dropdown')),'selection':obj(singleSelect=lit(False),selectAllCheckboxEnabled=lit(True)),'header':obj(show=lit(True),fontColor=color(MUTED),textSize=lit(10))},sync=sync)

def card(page,name,measure,pos,title,precision=1,units=1,accent=TEAL):
    visual(page,name,'card',pos,{'Values':[meas(measure)]},
            objects={'labels':obj(color=color(accent),fontSize=lit(39),fontFamily=lit('Segoe UI Semibold'),labelDisplayUnits=lit(units),labelPrecision=lit(precision)),
                     'categoryLabels':obj(show=lit(False))},title=title)

def chartstyle(accent=TEAL):
    return {'legend':obj(show=lit(False)), 'dataPoint':obj(defaultColor=color(accent)),
            'categoryAxis':obj(fontSize=lit(11),fontFamily=lit('Segoe UI'),labelColor=color(MUTED),showAxisTitle=lit(False)),
            'valueAxis':obj(fontSize=lit(10),labelColor=color(MUTED),showAxisTitle=lit(False),gridlineShow=lit(True),gridlineColor=color('#E8EDF0')),
            'labels':obj(show=lit(True),color=color(INK),fontSize=lit(10),labelDisplayUnits=lit(1),labelPrecision=lit(0))}

def make_pages():
    pages=[('delivery_overview','Delivery & Experience'),('improvement_priorities','Improvement Priorities')]
    write(REPORT/'definition/pages/pages.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json','pageOrder':[p for p,_ in pages],'activePageName':pages[0][0]})
    for n,(page,title) in enumerate(pages,1):
        scope=eqfilter('Date','Core Period',1);scope.update(displayName='Core period: Jan 2017–Aug 2018',isLockedInViewMode=True)
        write(REPORT/f'definition/pages/{page}/page.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json','name':page,'displayName':title,'displayOption':'FitToPage','width':1600,'height':900,'filterConfig':{'filters':[scope]},'objects':{'background':obj(color=color(BG),transparency=lit(0))}})
        textbox(page,'header-background',(0,0,1600,126),[('',10,INK,False)],INK)
        textbox(page,'header-title',(30,6,1150,114),[('OLIST  /  COMMERCE INTELLIGENCE',11,MINT,True),(title,29,'#FFFFFF',True),('Delivery promises, customer experience and evidence-led operational priorities',12,'#C5D6E0',False)])
        textbox(page,'page-marker',(1240,29,320,65),[(f'0{n}  /  OPERATIONS BRIEF',12,MINT,True),('BRAZIL  ·  2017–AUG 2018',10,'#D9E4E9',False)])
        textbox(page,'filter-note',(28,143,790,61),[('PURCHASE COHORT  /  JAN 2017–AUG 2018',11,INK,True),('Select a month or customer state. Click a chart to explore; clear selections to reset.',10,MUTED,False)])
        slicer(page,'month-filter',(850,142,338,64),field('Date','Month Label'),'PurchaseMonth')
        slicer(page,'state-filter',(1208,142,352,64),field('State','State'),'CustomerState')
        if n==1:
            specs=[('Eligible Delivered','Eligible delivered orders',0,1,TEAL),('On-time Delivery','On time · eligible deliveries',1,1,TEAL),('Median Delivery Days','Median delivery · elapsed days',1,1,INK),('Average Review','Avg review · all reviewed orders',2,1,INK)]
        else:
            specs=[('Late Orders','Late eligible orders',0,1,ORANGE),('Late Order Exposure BRL','Late-order merchandise · BRL',2,1000000,ORANGE),('P90 Delivery Days','P90 delivery · elapsed days',1,1,INK),('Seller Coverage','Single-seller diagnostic coverage',1,1,TEAL)]
        for i,(measure,title2,precision,units,accent) in enumerate(specs):card(page,f'kpi-{i}',measure,(40+i*385,218,365,114),title2,precision,units,accent)
        if n==1:
            style=chartstyle();style['labels']=obj(show=lit(False));style['legend']=obj(show=lit(True),position=lit('Top'),fontSize=lit(10));style['valueAxis'][0]['properties'].update(secShow=lit(True),secStart=lit(0),secEnd=lit(1),secShowAxisTitle=lit(False));style['dataPoint']=obj(defaultColor=color(TEAL))
            visual(page,'monthly','lineClusteredColumnComboChart',(40,350,916,230),{'Category':[field('Date','Month Label')],'Y':[meas('Eligible Delivered')],'Y2':[meas('On-time Delivery')],'Tooltips':[meas('Late Orders'),meas('Median Delivery Days'),meas('Average Review')]},style,'Volume and promise adherence','Purchase cohorts · on-time rate uses eligible delivered orders',sort=(field('Date','Month Label'),'Ascending'))
            visual(page,'states','clusteredBarChart',(982,350,578,492),{'Category':[field('State','State')],'Y':[meas('Late Orders')],'Tooltips':[meas('Eligible Delivered'),meas('Late Rate'),meas('Median Delivery Days')]},chartstyle(ORANGE),'Where late orders accumulate','Top late-count ranks · minimum 100 eligible orders',filters=[eqfilter('Order','State Priority Flag',1,True)],sort=(meas('Late Orders'),'Descending'))
            ratingstyle=chartstyle();ratingstyle['legend']=obj(show=lit(True),position=lit('Top'),fontSize=lit(10));ratingstyle['labels']=obj(show=lit(False))
            ratingstyle['dataPoint']=[{'selector':{'data':[{'scopeId':{'Comparison':{'ComparisonKind':0,'Left':field('Order','Review Score'),'Right':{'Literal':{'Value':str(score)+'L'}}}}}]},'properties':{'fill':color(c)}} for score,c in enumerate(['#C85247','#E59B69','#D9C47B','#75B6A1','#1A7D72'],1)]
            review_id=visual(page,'reviews','hundredPercentStackedBarChart',(40,600,916,242),{'Category':[field('Order','Delay Band')],'Y':[meas('Post-delivery Reviews')],'Series':[field('Order','Review Score')],'Tooltips':[meas('Post-delivery Low Rating'),meas('Post-delivery Band Reviews'),meas('Post-delivery Coverage')]},ratingstyle,'Customer reviews after delivery','Selected responses; survey timing creates unequal coverage',sort=(field('Order','Delay Band'),'Ascending'))
            review_path=REPORT/f'definition/pages/{page}/visuals/{review_id}/visual.json'
            review_json=json.loads(review_path.read_text())
            review_json['visual']['visualContainerObjects']['subTitle'][0]['properties']['text']={'expr':meas('Review Timing Note')}
            write(review_path,review_json)
        else:
            visual(page,'category-priorities','clusteredBarChart',(40,350,760,492),{'Category':[field('Category','Category')],'Y':[meas('Category Late Orders')],'Tooltips':[meas('Category Eligible'),meas('Category Late Rate'),meas('Average Review')]},chartstyle(ORANGE),'Prioritize material category volumes','Single-category orders · minimum 100 eligible · ranked by late orders',filters=[eqfilter('Order','Category Priority Flag',1,True)],sort=(meas('Category Late Orders'),'Descending'))
            table_style={'grid':obj(gridVertical=lit(False),gridHorizontal=lit(True),gridHorizontalColor=color('#E8EDF0'),rowPadding=lit(0)),'columnHeaders':obj(fontColor=color(MUTED),backColor=color('#F6F8F9'),fontSize=lit(11),autoSizeColumnWidth=lit(False)),'values':obj(fontColorPrimary=color(INK),fontSize=lit(11)),'total':obj(totals=lit(False))}
            seller_style=copy.deepcopy(table_style)
            seller_style['columnWidth']=[{'selector':{'metadata':query},'properties':{'value':lit(width)}} for query,width in [('Seller.Seller',200),('Order.Seller Eligible',110),('Order.Seller Late Orders',90),('Order.Seller Late Rate',110),('Order.Median Handoff Days',160)]]
            visual(page,'seller-priorities','tableEx',(826,350,734,290),{'Values':[field('Seller','Seller'),meas('Seller Eligible'),meas('Seller Late Orders'),meas('Seller Late Rate'),meas('Median Handoff Days')]},seller_style,'Seller investigation queue','Single-seller orders · at least 100 eligible · investigate before assigning fault',filters=[eqfilter('Order','Seller Priority Flag',1,True)],sort=(meas('Seller Late Orders'),'Descending'))
            stage_style=copy.deepcopy(table_style)
            stage_style['columnWidth']=[{'selector':{'metadata':query},'properties':{'value':lit(width)}} for query,width in [('Stage.Stage',227),('Order.Median Stage Days',190),('Order.Valid Stage Orders',230)]]
            visual(page,'stage-times','tableEx',(826,662,734,180),{'Values':[field('Stage','Stage'),meas('Median Stage Days'),meas('Valid Stage Orders')]},stage_style,'Where elapsed time sits','Valid samples by stage · medians are not additive',sort=(field('Stage','Stage'),'Ascending'))
        note='DEFINITIONS  /  On time = actual calendar date ≤ promised calendar date. Missing outcomes excluded from delivery rates; review coverage varies.' if n==1 else 'ACTION  /  Investigate concentrated delays by destination and cohort before selecting a pilot. Multi-seller/category orders remain in overall KPIs.'
        textbox(page,'footer',(40,854,1520,46),[(note,10,INK,False),('SOURCE  Olist via Kaggle · CC BY-NC-SA 4.0 · BRL values are merchandise/freight charges, not profit or lost revenue.',9,MUTED,False)])

def main():
    manifest=json.loads((ROOT/'reports/validation/build_manifest.json').read_text())
    independent=json.loads((ROOT/'reports/validation/independent_validation.json').read_text())
    assert independent['status']=='PASS' and not any(c['failures'] for c in manifest['hard_checks'])
    seed=ROOT/'assets/powerbi_seed'
    shutil.copytree(seed/'StaticResources',REPORT/'StaticResources',dirs_exist_ok=True)
    for name in ['report.json','version.json']:
        definition=json.loads((seed/f'definition/{name}').read_text())
        if name=='report.json':definition.setdefault('settings',{})['defaultFilterActionIsDataFilter']=True
        write(REPORT/f'definition/{name}',definition)
    write(DEST/f'{PROJECT}.pbip',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':f'{PROJECT}.Report'}}],'settings':{'enableAutoRecovery':True}})
    write(REPORT/'definition.pbir',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':f'../{PROJECT}.SemanticModel'}}})
    make_model(manifest)
    make_pages()
    print(f'Generated {DEST/PROJECT}.pbip; {len(TABLES)} import tables; {len(MEASURES)} explicit measures; 2 pages. Desktop refresh/validation is still required.')

if __name__=='__main__':main()
