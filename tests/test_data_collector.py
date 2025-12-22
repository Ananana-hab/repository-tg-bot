
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_collector import DataCollector

class TestDataCollector(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.collector = DataCollector()
        
    @patch('ccxt.async_support.binance')
    async def test_get_market_data_success(self, mock_binance_class):
        # Clear cache
        self.collector._fng_cache = {'value': None, 'ts': None}
        
        # Mock exchange instance
        mock_exchange = mock_binance_class.return_value
        
        # Configure exchange methods (AsyncMock)
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1600000000000 + i*60000, 50000+i, 51000+i, 49000+i, 50500+i, 100+i] 
            for i in range(100)
        ])
        mock_exchange.fetch_order_book = AsyncMock(return_value={'bids': [[50000, 1]], 'asks': [[50100, 1]]})
        mock_exchange.fetch_ticker = AsyncMock(return_value={'last': 50500, 'quoteVolume': 1000})
        mock_exchange.close = AsyncMock()
        
        # Assign mock to collector
        self.collector.exchange = mock_exchange
        
        # Mock aiohttp for F&G and OI
        with patch('aiohttp.ClientSession') as mock_session_cls:
             mock_session = mock_session_cls.return_value
             mock_session.__aenter__.return_value = mock_session
             mock_session.__aexit__.return_value = None
             
             # Create mock response objects for different calls
             mock_fg_response = AsyncMock()
             mock_fg_response.status = 200
             mock_fg_response.json.return_value = {'data': [{'value': '55', 'value_classification': 'Greed'}]}
             
             mock_oi_response = AsyncMock()
             mock_oi_response.status = 200
             mock_oi_response.json.return_value = {'openInterest': '500000'}

             # Create async context managers for get() calls
             fg_ctx = MagicMock()
             fg_ctx.__aenter__.return_value = mock_fg_response
             fg_ctx.__aexit__.return_value = None
             
             oi_ctx = MagicMock()
             oi_ctx.__aenter__.return_value = mock_oi_response
             oi_ctx.__aexit__.return_value = None

             # Side effect to return appropriate context manager
             def side_effect_(*args, **kwargs):
                 if 'alternative.me' in args[0]:
                     return fg_ctx
                 elif 'fapi.binance.com' in args[0]:
                     return oi_ctx
                 return fg_ctx # default
                 
             mock_session.get.side_effect = side_effect_
             
             # Run test
             data = await self.collector.get_market_data()
             
             self.assertIsNotNone(data)
             self.assertIn('df', data)
             self.assertIn('orderbook', data)
             self.assertEqual(data['fear_greed'], 55)
             self.assertEqual(data['open_interest'], 500000.0)

    @patch('aiohttp.ClientSession')
    async def test_fear_greed_fallback(self, mock_session_cls):
        # Clear cache
        self.collector._fng_cache = {'value': None, 'ts': None}
        
        mock_session = mock_session_cls.return_value
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        # Simulate network error
        mock_session.get.side_effect = Exception("API Error")
        
        index = await self.collector.get_fear_greed_index()
        self.assertEqual(index, 50)

if __name__ == '__main__':
    unittest.main()
