"""Regression tests for false-PASS conditions found during the final audit."""
import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
import duckdb

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('model_validator',ROOT/'tests/validate_powerbi_results.py')
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)

class ValidationGuards(unittest.TestCase):
    def test_m_path_quoting_preserves_apostrophes_and_unicode(self):
        sys.path.insert(0,str(ROOT/'src'))
        from make_report import m_quote
        self.assertEqual(m_quote("D:/Portfolio/O'Brien/Ã¸/data"),'"D:/Portfolio/O\'Brien/Ã¸/data"')
        self.assertEqual(m_quote('a"b'),'"a""b"')

    def test_blank_is_not_zero_currency(self):
        with self.assertRaises(AssertionError):validator.close(None,'0.00')

    def test_missing_baselines_fail(self):
        original=validator.read
        with patch.object(validator,'read',side_effect=lambda name: {'rows':[]} if name=='model_baselines.json' else original(name)):
            with self.assertRaisesRegex(AssertionError,'baseline'):validator.main()

    def test_duplicate_scopes_fail(self):
        original=validator.read;all_row=original('model_baselines.json')['rows'][0]
        with patch.object(validator,'read',side_effect=lambda name: {'rows':[all_row,all_row]} if name=='model_baselines.json' else original(name)):
            with self.assertRaisesRegex(AssertionError,'baseline'):validator.main()

    def test_missing_diagnostics_fail(self):
        original=validator.read
        with patch.object(validator,'read',side_effect=lambda name: {'rows':[]} if name=='model_diagnostics.json' else original(name)):
            with self.assertRaisesRegex(AssertionError,'diagnostic'):validator.main()

    def test_optimized_python_is_rejected(self):
        result=subprocess.run([sys.executable,'-O',str(ROOT/'tests/validate_powerbi_results.py')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('without Python -O',result.stderr)

    def test_sql_mutations_are_detected(self):
        # Operate only on a new, uniquely named copy. No canonical data is changed.
        sandbox=ROOT/'.cache'/f'guard-{uuid.uuid4().hex}.duckdb'
        sandbox.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT/'data/commerce.duckdb',sandbox)
        con=duckdb.connect(str(sandbox));con.execute("SET memory_limit='256MB'");con.execute('SET threads=2')
        sql=(ROOT/'sql/03_tests.sql').read_text()
        mutations=[("UPDATE mart.fact_order SET is_late=NULL WHERE order_id=(SELECT min(order_id) FROM mart.fact_order WHERE delivery_eligible=1)",'delivery_partition'),
                   ("UPDATE mart.fact_order SET delivery_days=NULL WHERE order_id=(SELECT min(order_id) FROM mart.fact_order WHERE delivery_eligible=1)",'duration_null_contract'),
                   ("UPDATE mart.fact_order SET is_late=1-is_late WHERE order_id=(SELECT min(order_id) FROM mart.fact_order WHERE delivery_eligible=1)",'late_date_consistency')]
        try:
            for mutation,check in mutations:
                con.execute('BEGIN')
                try:
                    con.execute(mutation)
                    failures=dict(con.execute(sql).fetchall())
                    self.assertGreater(failures[check],0,check)
                finally:con.execute('ROLLBACK')
        finally:con.close()

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ValidationGuards)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    evidence={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
              'failures':len(result.failures),'errors':len(result.errors),'sql_mutations_checked':3,
              'note':'Mutation inputs exist only in an isolated copied test database; portfolio findings always use authentic unmodified source data.'}
    (ROOT/'reports/validation/guard_tests.json').write_text(json.dumps(evidence,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
