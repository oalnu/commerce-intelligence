"""One-command local ingestion, SQL, analysis, independent checks and PBIP generation."""
import argparse
from build import build
from analyze import main as analyze
from validate_independent import run as validate
from make_report import main as report
from audit_findings import main as audit

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',help='Optional original Olist ZIP, verified against the pinned SHA-256.')
    args=parser.parse_args()
    build(args.archive)
    analyze()
    validate()
    audit()
    report()
    print('Pipeline complete. Open powerbi/CommerceIntelligence.pbip in Desktop; Transform data > Close & Apply, then Refresh and run the DAX/UI checks.')
