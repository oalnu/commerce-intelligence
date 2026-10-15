"""Rebuild Commerce Intelligence from the pinned, authentic Olist archive."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import shutil
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    'customers': 'olist_customers_dataset.csv',
    'geolocation': 'olist_geolocation_dataset.csv',
    'order_items': 'olist_order_items_dataset.csv',
    'order_payments': 'olist_order_payments_dataset.csv',
    'order_reviews': 'olist_order_reviews_dataset.csv',
    'orders': 'olist_orders_dataset.csv',
    'products': 'olist_products_dataset.csv',
    'sellers': 'olist_sellers_dataset.csv',
    'product_category_name_translation': 'product_category_name_translation.csv',
}
MARTS = ['fact_order','fact_item','dim_date','dim_customer_state','dim_seller','dim_category','dim_product','dim_status','dim_stage']

def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def json_write(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, default=str, ensure_ascii=False)+'\n', encoding='utf-8')

def file_literal(path):
    return "'"+str(Path(path).resolve()).replace('\\','/').replace("'","''")+"'"

def records(con, sql):
    result = con.execute(sql)
    fields = [x[0] for x in result.description]
    return [dict(zip(fields,row)) for row in result.fetchall()]

def acquire(manifest, archive_override):
    raw = ROOT/'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    missing = [key for key,name in NAMES.items() if not (raw/name).is_file()]
    if missing:
        archive = Path(archive_override).resolve() if archive_override else raw/'olist.zip'
        if archive_override and not archive.is_file():
            raise FileNotFoundError(f'The supplied source archive does not exist: {archive}')
        if not archive.is_file():
            print('Downloading original Olist Kaggle archive...', flush=True)
            pending=archive.with_suffix('.zip.download')
            with urllib.request.urlopen(manifest['download_url'],timeout=90) as response, pending.open('wb') as out:
                shutil.copyfileobj(response,out)
            if digest(pending)!=manifest['archive_sha256']:
                raise ValueError('Downloaded archive checksum changed; unverified bytes were not promoted to the cache.')
            pending.replace(archive)
        if digest(archive) != manifest['archive_sha256']:
            raise ValueError('Archive checksum changed. Review and deliberately update the source pin before rebuilding.')
        with zipfile.ZipFile(archive) as z:
            for key in missing:
                name = NAMES[key]
                (raw/name).write_bytes(z.read(name))
    for key,name in NAMES.items():
        path = raw/name
        if digest(path) != manifest['tables'][key]['sha256']:
            raise ValueError(f'Source file checksum mismatch: {name}')
        with path.open(encoding='utf-8-sig',newline='') as f:
            if next(csv.reader(f)) != manifest['tables'][key]['columns']:
                raise ValueError(f'Source schema mismatch: {name}')
    return raw

def build(archive=None, database=None):
    started = time.perf_counter()
    manifest = json.loads((ROOT/'config/source_manifest.json').read_text())
    raw = acquire(manifest, archive)
    processed = ROOT/'data/processed'
    processed.mkdir(parents=True, exist_ok=True)
    evidence = ROOT/'reports/validation'
    evidence.mkdir(parents=True, exist_ok=True)
    database = Path(database).resolve() if database else ROOT/'data/commerce.duckdb'
    if not database.is_relative_to(ROOT):raise ValueError('Build databases must stay inside this project.')
    database.parent.mkdir(parents=True,exist_ok=True)
    con = duckdb.connect(str(database))
    con.execute("SET memory_limit='512MB'")
    con.execute('SET threads=2')
    con.execute("SET preserve_insertion_order=false")
    con.execute('BEGIN')
    try:
        con.execute('CREATE SCHEMA IF NOT EXISTS raw')
        for key,name in NAMES.items():
            table = 'category_translation' if key=='product_category_name_translation' else key
            con.execute(f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM read_csv({file_literal(raw/name)}, header=true, all_varchar=true, strict_mode=true)")
            count = con.execute(f'SELECT count(*) FROM raw.{table}').fetchone()[0]
            if count != manifest['tables'][key]['rows']:
                raise ValueError(f'Source row count mismatch for {table}: {count}')
            print(f'Ingested {table}: {count:,} rows',flush=True)
        for file in ['01_staging.sql','02_marts.sql']:
            con.execute((ROOT/'sql'/file).read_text(encoding='utf-8'))
        checks = records(con,(ROOT/'sql/03_tests.sql').read_text())
        failed = [c for c in checks if c['failures'] != 0]
        if failed:
            raise ValueError(f'Hard validation failures: {failed}')
        con.execute('COMMIT')
    except Exception:
        con.execute('ROLLBACK')
        raise
    exports = {}
    for table in MARTS:
        path = processed/f'{table}.csv'
        temporary = processed/f'{table}.csv.tmp'
        # Stable export order makes repeated builds comparable byte for byte.
        order = 'order_id, item_number' if table=='fact_item' else con.execute(f'DESCRIBE mart.{table}').fetchone()[0]
        con.execute(f'COPY (SELECT * FROM mart.{table} ORDER BY {order}) TO {file_literal(temporary)} (HEADER, DELIMITER \',\')')
        temporary.replace(path)
        exports[table] = {'rows':con.execute(f'SELECT count(*) FROM mart.{table}').fetchone()[0],
                          'sha256':digest(path),'columns':records(con,f'DESCRIBE mart.{table}')}
    for table in ['source_exceptions','payment_reconciliation','quality_summary']:
        path = evidence/f'{table}.csv'
        con.execute(f'COPY (SELECT * FROM audit.{table} ORDER BY 1,2) TO {file_literal(path)} (HEADER, DELIMITER \',\')')
    baselines = {}
    for scope,condition in [('all','true'),('core','core_period=1')]:
        baselines[scope] = records(con,f'''
            SELECT count(*) orders, sum(delivery_eligible) eligible, sum(is_late) late,
                count(*) FILTER(WHERE order_status='delivered') delivered,
                median(delivery_days) median_days, quantile_cont(delivery_days,0.9) p90_days,
                avg(review_score) average_review, count(review_score) reviewed,
                count(*) FILTER(WHERE review_score<=2) low_reviews,
                sum(merchandise_brl) FILTER(WHERE order_status='delivered') delivered_merchandise_brl,
                sum(freight_brl) FILTER(WHERE order_status='delivered') delivered_freight_brl
            FROM mart.fact_order WHERE {condition}''')[0]
    json_write(evidence/'sql_baselines.json',baselines)
    slices = records(con,"""SELECT d.month_label, f.customer_state, count(*) orders,
            sum(delivery_eligible) eligible, coalesce(sum(is_late),0) late,
            sum(merchandise_brl) merchandise_brl, sum(freight_brl) freight_brl
        FROM mart.fact_order f JOIN mart.dim_date d USING(date_key)
        GROUP BY 1,2 ORDER BY 1,2""")
    json_write(evidence/'sql_month_state_slices.json',slices)
    json_write(evidence/'build_manifest.json',{
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'source_archive_sha256':manifest['archive_sha256'],'duckdb_version':duckdb.__version__,
        'memory_limit':'512MB','threads':2,'elapsed_seconds':round(time.perf_counter()-started,2),
        'hard_checks':checks,'exports':exports,
        'exceptions':records(con,'SELECT * FROM audit.quality_summary ORDER BY issue'),
        'note':'Source exceptions are audited, not erased. No joins of independent detail collections.'
    })
    con.close()
    print(f'PASS: {len(checks)} hard checks; exported {len(exports)} tables. {time.perf_counter()-started:.1f}s',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',help='Optional local original Kaggle ZIP; SHA-256 must match the pinned source.')
    args=parser.parse_args()
    build(args.archive)
