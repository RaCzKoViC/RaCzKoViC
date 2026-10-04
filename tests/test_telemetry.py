import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from project_telemetry import category, ci_state
from generate_stats import render
class TelemetryTests(unittest.TestCase):
 def test_categories(self):
  for path, expected in [('docs/example.py','source'),('README.md','documentation'),('.github/workflows/ci.yml','configuration'),('Cargo.lock','configuration'),('Dockerfile','configuration'),('docs/a.png',None),('target/a.rs',None),('src/node_modules/a.js',None)]:
   self.assertEqual(category(path),expected,path)
 def test_ci_does_not_fake_success(self):
  self.assertEqual(ci_state([]),'No CI for this commit')
  self.assertEqual(ci_state([{'status':'completed','conclusion':'skipped'}]),'Skipped / neutral')
  self.assertEqual(ci_state([{'status':'completed','conclusion':'failure'},{'status':'completed','conclusion':'success'}]),'Failed')
  self.assertEqual(ci_state([{'status':'in_progress'}]),'Running')
 def test_render_is_text_and_aligned(self):
  v=dict(lines=1234567,documentation=98765,configuration=12345,repos=6,stars=16,followers=2,forks=4,projects=[])
  portrait=('x'*48+'\n')*36
  result=render(v,'2026-10-04 05:00',portrait)
  self.assertIn('Lines of Code on GitHub',result)
  self.assertNotIn('<img',result)
  self.assertLess(result.index('Lines of Code on GitHub'),result.index('Public repos'))
if __name__=='__main__':unittest.main()
