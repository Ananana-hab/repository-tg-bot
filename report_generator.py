"""
Report Generator Module
Responsible for generating performance reports and visualizations
"""
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
import logging
from datetime import datetime
import matplotlib.dates as mdates

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, reports_dir="reports"):
        """
        Initialize ReportGenerator
        
        Args:
            reports_dir: Directory to save reports
        """
        self.reports_dir = reports_dir
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)
            
    def export_to_csv(self, signals_df, filename=None):
        """
        Export signals to CSV
        
        Args:
            signals_df: DataFrame with signals
            filename: Optional filename
            
        Returns:
            str: Path to saved file
        """
        if filename is None:
            filename = f"signals_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        filepath = os.path.join(self.reports_dir, filename)
        
        try:
            # Format columns for readability if needed
            export_df = signals_df.copy()
            
            # Save
            export_df.to_csv(filepath, index=False)
            logger.info(f"Exported signals to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return None

    def generate_equity_curve_chart(self, equity_curve_df, filename=None):
        """
        Generate equity curve visualization
        
        Args:
            equity_curve_df: DataFrame with 'timestamp' and 'equity' columns
            filename: Optional filename
            
        Returns:
            str: Path to saved image or buffer
        """
        if filename is None:
            filename = f"equity_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
        filepath = os.path.join(self.reports_dir, filename)
        
        try:
            plt.figure(figsize=(12, 6))
            plt.plot(pd.to_datetime(equity_curve_df['timestamp']), equity_curve_df['equity'], label='Equity', color='#1f77b4', linewidth=2)
            
            # Styling
            plt.title('Equity Curve', fontsize=14)
            plt.xlabel('Date')
            plt.ylabel('Capital ($)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Formatting dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()
            
            # Background statistics box
            total_return = (equity_curve_df['equity'].iloc[-1] - equity_curve_df['equity'].iloc[0]) / equity_curve_df['equity'].iloc[0] * 100
            stats_text = f"Total Return: {total_return:+.2f}%"
            plt.text(0.02, 0.95, stats_text, transform=plt.gca().transAxes, 
                     bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))

            # Save
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Generated equity curve chart at {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating equity curve chart: {e}")
            plt.close() # Ensure cleanup
            return None

    def generate_drawdown_chart(self, equity_curve_df, filename=None):
        """
        Generate drawdown visualization
        """
        if filename is None:
            filename = f"drawdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
        filepath = os.path.join(self.reports_dir, filename)
        
        try:
            # Calculate drawdown
            equity = equity_curve_df['equity']
            peak = equity.cummax()
            drawdown = (equity - peak) / peak * 100
            
            plt.figure(figsize=(12, 4))
            plt.fill_between(pd.to_datetime(equity_curve_df['timestamp']), drawdown, 0, color='red', alpha=0.3, label='Drawdown')
            plt.plot(pd.to_datetime(equity_curve_df['timestamp']), drawdown, color='red', linewidth=1)
            
            plt.title('Drawdown (%)', fontsize=14)
            plt.xlabel('Date')
            plt.ylabel('Drawdown %')
            plt.grid(True, alpha=0.3)
            
            # Formatting
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()
            
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Generated drawdown chart at {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error generating drawdown chart: {e}")
            plt.close()
            return None
