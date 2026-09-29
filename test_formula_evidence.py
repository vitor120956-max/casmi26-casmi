import unittest
from formula_evidence import adduct_charge,split_spectra,combine_formula_evidence
class FormulaEvidenceTests(unittest.TestCase):
 def row(self,adduct='[M+H]+',mode='positive',precursor=101,mz=None):
  return dict(molecule_id='a',adduct=adduct,ionization_mode=mode,precursor_mz=precursor,ms2_mzs=mz or [60,20],ms2_normalized_intensities=[1,0.5])
 def test_charge(self):
  for add,charge in [('[M+H]+',1),('[M-H]-',-1),('[M+2H]2+',2),('[M+CH2O2-H]-',-1)]:self.assertEqual(adduct_charge(add),charge)
 def test_mixed_adducts_stay_separate(self):
  groups=split_spectra([self.row(),self.row('[M-H]-','negative',99)])
  self.assertEqual(len(groups),2);self.assertEqual({g['precursor_mz'] for g in groups},{99,101})
 def test_same_adduct_merged_and_sorted(self):
  g=split_spectra([self.row(precursor=100),self.row(precursor=102)])[0]
  self.assertEqual(g['precursor_mz'],101);self.assertEqual(g['ms2_mzs'],[20,20,60,60]);self.assertEqual(g['spectrum_count'],2)
 def test_rejects_inconsistent_polarity(self):
  with self.assertRaises(ValueError):split_spectra([self.row(mode='negative')])
 def group(self,adduct,formulas,mode='positive'):return dict(molecule_id='a',adduct=adduct,mode=mode,formulas=formulas)
 def test_supported_formula_beats_single_group_formula(self):
  result=combine_formula_evidence([self.group('[M+H]+',['A','B']),self.group('[M+Na]+',['C','B'])]);self.assertEqual(result['a'][0],'B')
 def test_one_group_preserves_formula_order(self):
  self.assertEqual(combine_formula_evidence([self.group('[M+H]+',['C','B','A'])])['a'],['C','B','A'])
 def test_duplicate_groups_rejected(self):
  with self.assertRaises(ValueError):combine_formula_evidence([self.group('[M+H]+',['A']),self.group('[M+H]+',['A'])])
 def test_duplicate_formula_within_group_not_double_vote(self):
  result=combine_formula_evidence([self.group('[M+H]+',['A','A','B']),self.group('[M+Na]+',['B'])]);self.assertEqual(result['a'][0],'B')
 def test_no_formulas_does_not_drop_molecule(self):self.assertEqual(combine_formula_evidence([self.group('[M+H]+',[])]),{'a':[]})
if __name__=='__main__':unittest.main(verbosity=2)
