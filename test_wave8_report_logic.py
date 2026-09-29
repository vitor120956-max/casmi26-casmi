import unittest
from wave8_report_logic import next_step
class ResultTests(unittest.TestCase):
 def test_all_rejected(self):
  s=next_step([{'status':'COMPLETE','errorDescription':'rerun error'}]*5)
  self.assertIn('Lote encerrado',s);self.assertNotIn('Aguardar as notas faltantes',s)
 def test_pending(self):self.assertIn('Aguardar as notas faltantes',next_step([{'status':'PENDING'}]*5))
 def test_mixed(self):
  s=next_step([{'status':'PENDING'}]*4+[{'status':'COMPLETE','errorDescription':'error'}])
  self.assertIn('4 resultado(s)',s);self.assertIn('diagnosticar',s)
 def test_missing(self):self.assertIn('Aguardar',next_step([]))
 def test_complete_score_zero(self):self.assertIn('Lote encerrado',next_step([{'status':'COMPLETE','publicScore':'0'}]*5))
if __name__=='__main__':unittest.main()
