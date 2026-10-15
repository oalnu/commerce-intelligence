"""Execute versioned analytical SQL and retain inspectable, reproducible evidence."""
import csv
import json
import math
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]

def wilson(k,n):
    z=1.96;p=k/n;den=1+z*z/n;center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [center-half,center+half]

def main():
    con=duckdb.connect(str(ROOT/'data/commerce.duckdb'),read_only=True)
    con.execute("SET memory_limit='256MB'")
    con.execute('SET threads=2')
    destination=ROOT/'reports/analysis';destination.mkdir(parents=True,exist_ok=True)
    for path in sorted((ROOT/'sql/analysis').glob('*.sql')):
        result=con.execute(path.read_text(encoding='utf-8'))
        fields=[x[0] for x in result.description]
        rows=[dict(zip(fields,r)) for r in result.fetchall()]
        if path.stem.startswith('03_'):
            for row in rows:row['low_rating_wilson_95']=wilson(row['low_reviews'],row['reviewed_orders'])
        (destination/f'{path.stem}.json').write_text(json.dumps(rows,indent=2,default=str,ensure_ascii=False)+'\n',encoding='utf-8')
        with (destination/f'{path.stem}.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else fields);writer.writeheader();writer.writerows(rows)
        print(f'{path.stem}: {len(rows)} rows',flush=True)
    con.close()

if __name__=='__main__':main()
