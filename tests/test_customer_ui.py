"""Run locally after installing Streamlit: python -m tests.test_customer_ui."""
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
CID = '8d50f5eadf50201ccdcedfb9e2ac8455'
OID = 'd3582fd5ccccd9cb229a63dfb417c86f'


def by_label(elements, label):
    return next(e for e in elements if e.label == label)


class CustomerUITests(unittest.TestCase):
    def test_customer_flow(self):
        at = AppTest.from_file(str(ROOT / 'pages' / '02_Customer.py'), default_timeout=30).run()
        self.assertFalse(at.exception, str(at.exception))
        first = at.dataframe[0].value
        self.assertEqual(len(first), 20)
        by_label(at.button, 'Next').click().run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertTrue(set(first.customer_unique_id).isdisjoint(at.dataframe[0].value.customer_unique_id))
        by_label(at.button, 'Previous').click().run()
        self.assertEqual(first.customer_unique_id.tolist(), at.dataframe[0].value.customer_unique_id.tolist())
        by_label(at.text_input, 'Customer ID / prefix').set_value('8d50f5')
        by_label(at.selectbox, 'State').select('SP')
        by_label(at.button, 'Search').click().run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertEqual(at.dataframe[0].value.customer_unique_id.tolist(), [CID])
        by_label(at.selectbox, 'Select customer').select(CID)
        by_label(at.button, 'View customer').click().run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertEqual(by_label(at.metric, 'Total orders').value, '17')
        self.assertEqual(by_label(at.metric, 'Delivered orders').value, '15')
        self.assertEqual(by_label(at.metric, 'Delivered spend (BRL)').value, 'R$ 879.27')
        self.assertEqual(len(at.dataframe[1].value), 17)
        by_label(at.selectbox, 'Select an order').select(OID).run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertAlmostEqual(float(at.dataframe[2].value.item_total.iloc[0]), 38.66)
        by_label(at.selectbox, 'State').select('RJ')
        by_label(at.button, 'Search').click().run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertTrue(any('No customers on this page' in m.value for m in at.info))
        self.assertEqual(len(at.metric), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
