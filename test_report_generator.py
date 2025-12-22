
import unittest
import pandas as pd
import os
import shutil
from report_generator import ReportGenerator

class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_reports"
        self.rg = ReportGenerator(reports_dir=self.test_dir)
        
        # Create dummy data
        self.signals_data = {
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'signal': ['PUMP', 'DUMP'] * 5,
            'price': [100, 101, 102, 99, 98, 97, 100, 105, 104, 103],
            'result': [1, -0.5, 2, 0, 1, 0, 0, 3, -1, 0]
        }
        self.signals_df = pd.DataFrame(self.signals_data)
        
        self.equity_data = {
            'timestamp': pd.date_range(start='2024-01-01', periods=10),
            'equity': [1000, 1010, 1005, 1025, 1030, 1020, 1040, 1070, 1060, 1060]
        }
        self.equity_df = pd.DataFrame(self.equity_data)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_export_to_csv(self):
        filepath = self.rg.export_to_csv(self.signals_df, "test_signals.csv")
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        
        # Read back
        df = pd.read_csv(filepath)
        self.assertEqual(len(df), 10)

    def test_generate_equity_curve_chart(self):
        filepath = self.rg.generate_equity_curve_chart(self.equity_df, "test_equity.png")
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.endswith(".png"))

    def test_generate_drawdown_chart(self):
        filepath = self.rg.generate_drawdown_chart(self.equity_df, "test_drawdown.png")
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))

if __name__ == '__main__':
    unittest.main()
