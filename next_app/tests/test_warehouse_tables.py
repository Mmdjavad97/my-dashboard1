import copy
import re
import unittest
from next_app.backend import reports

class WarehouseTableTests(unittest.TestCase):
    def test_legacy_form_is_one_page_and_unchanged(self):
        form = reports.create_empty_warehouse_form()
        form.pop('extra_tables')
        form['items'][0] = ['ITEM-A', 'Description', '12', 'Project', 'Note']
        original = copy.deepcopy(form)
        pdf = reports.create_warehouse_pdf(form, reports.load_warehouse_template())
        self.assertEqual(len(re.findall(rb'/Type\s*/Page\b', pdf)), 1)
        self.assertEqual(form, original)

    def test_all_added_tables_and_values_are_paged_without_mutation(self):
        form = reports.create_empty_warehouse_form()
        form['extra_tables'] = [[['T2-'+str(i), 'شرح', str(i), 'Project', 'Note'] for i in range(10)],
                                [['T3-'+str(i), 'شرح سوم', str(i), 'Project', 'Note'] for i in range(10)]]
        original = copy.deepcopy(form)
        pages = reports.warehouse_pdf_tables(form)
        self.assertEqual(len(pages), 3)
        self.assertEqual(pages[1], form['extra_tables'][0])
        self.assertEqual(pages[2], form['extra_tables'][1])
        pdf = reports.create_warehouse_pdf(form, reports.load_warehouse_template())
        self.assertEqual(len(re.findall(rb'/Type\s*/Page\b', pdf)), 3)
        self.assertEqual(form, original)

    def test_legacy_oversized_table_keeps_its_remaining_rows(self):
        form = reports.create_empty_warehouse_form()
        form['items'] = [[str(i), '', '', '', ''] for i in range(13)]
        pages = reports.warehouse_pdf_tables(form)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[1][2][0], '12')
        self.assertEqual(pages[1][3], ['']*5)
        self.assertEqual(len(form['items']), 13)
