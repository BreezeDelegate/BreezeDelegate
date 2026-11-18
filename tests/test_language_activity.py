import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

script=Path(__file__).resolve().parents[1]/'scripts'/'render_language_activity.py'
spec=importlib.util.spec_from_file_location('render_language_activity',script)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class LanguageActivityTests(unittest.TestCase):
    def test_source_and_outputs(self):
        public=''.join('<div class="field language details"><div class="field"><svg><path fill="'+color+'" /></svg>'+name+'</div><small><div>some lines</div><div>'+str(pct)+'%</div></small></div>' for name,pct,color in [('Python',40.85,'#3572A5'),('Go',20.07,'#00ADD8'),('Rust',39.08,'#dea584')])
        priv=''.join('<span style="display:block;background:'+color+'"></span><span>'+name+' '+str(pct)+'%</span>' for name,pct,color in [('JavaScript',21,'#f1e05a'),('TypeScript',20,'#3178C6'),('Python',18,'#3572A5'),('Other',41,'#8c959f')])
        svg='Private languages'+priv+'Most used languages'+public
        pub,private=mod.read_source(svg)
        self.assertEqual(len(pub),3)
        self.assertEqual(len(private),4)
        self.assertAlmostEqual(sum(v for _,v,_ in pub),100)
        for mobile in (False,True):
            for dark in (False,True):
                s=mod.render_svg(pub,private,dark,mobile,'18 Nov 2026')
                ET.fromstring(s)
                self.assertIn('40.85%',s)
                self.assertIn('21%',s)
                self.assertEqual('width="430"' in s,mobile)
    def test_reject_bad_source(self):
        with self.assertRaises(ValueError):mod.read_source('No language data')

if __name__=='__main__':unittest.main()
