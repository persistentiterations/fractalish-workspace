import json, subprocess, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GUARDIAN=ROOT/'guardian.py'
CORPUS=Path(__file__).resolve().parent/'bypass_corpus'

class BypassCorpusTests(unittest.TestCase):
    def test_all_corpus_outcomes(self):
        expected=json.loads((CORPUS/'expected.json').read_text())
        failures=[]
        with tempfile.TemporaryDirectory() as temp:
            ledger=Path(temp)/'ledger.jsonl'
            for filename,wanted in sorted(expected.items()):
                result=subprocess.run(
                    ['/usr/bin/python3','-S',str(GUARDIAN),'--unsigned-dev','--ledger',str(ledger),'scan',str(CORPUS/filename),'--json'],
                    capture_output=True,text=True,timeout=10,
                )
                try: slip=json.loads(result.stdout)
                except json.JSONDecodeError:
                    failures.append(f'{filename}: invalid JSON output {result.stdout!r} {result.stderr!r}')
                    continue
                actual=slip['intake_outcome']
                if actual!=wanted:
                    failures.append(f'{filename}: expected {wanted}, got {actual}; caveats={slip.get("caveats")} results={slip.get("item_results")}')
        self.assertEqual(failures,[],"\n".join(failures))

if __name__=='__main__': unittest.main(verbosity=2)
