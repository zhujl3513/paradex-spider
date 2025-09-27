import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from typing import List, Dict, Optional, Tuple


class ParadexKlineAnalyzer:
    """Paradex K线数据获取和布林带指标计算类"""
    
    def __init__(self, base_url: str = "https://api.paradex.trade"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ParadexKlineAnalyzer/1.0',
            'Accept': 'application/json'
        })
        # 配置SSL和重试策略
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_klines(self, symbol: str, interval: str = "1m", 
                   start_time: Optional[datetime] = None, 
                   end_time: Optional[datetime] = None,
                   limit: int = 1000) -> List[Dict]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对符号 (例如: "ETH-USD")
            interval: 时间间隔 (1m, 5m, 15m, 1h, 4h, 1d)
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数据条数限制
            
        Returns:
            K线数据列表
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=30)  # 默认过去30天
        if end_time is None:
            end_time = datetime.now()
        
        # 转换时间戳
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        
        # 构建API请求URL
        url = f"{self.base_url}/api/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_ts,
            'endTime': end_ts,
            'limit': limit
        }
        
        try:
            print(f"正在获取 {symbol} 的K线数据...")
            print(f"时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 到 {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, dict) and 'data' in data:
                klines = data['data']
            elif isinstance(data, list):
                klines = data
            else:
                print(f"API返回数据格式异常: {data}")
                return []
            
            print(f"成功获取 {len(klines)} 条K线数据")
            return klines
            
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return []
        except Exception as e:
            print(f"获取K线数据时发生错误: {e}")
            return []
    
    def parse_klines_to_dataframe(self, klines: List[Dict]) -> pd.DataFrame:
        """
        将K线数据转换为DataFrame
        
        Args:
            klines: K线数据列表
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        if not klines:
            return pd.DataFrame()
        
        # 解析K线数据 (假设格式为: [timestamp, open, high, low, close, volume, ...])
        data = []
        for kline in klines:
            if isinstance(kline, list) and len(kline) >= 6:
                data.append({
                    'timestamp': kline[0],
                    'datetime': pd.to_datetime(kline[0], unit='ms'),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            elif isinstance(kline, dict):
                # 如果是字典格式，尝试提取字段
                data.append({
                    'timestamp': kline.get('timestamp', kline.get('time', 0)),
                    'datetime': pd.to_datetime(kline.get('timestamp', kline.get('time', 0)), unit='ms'),
                    'open': float(kline.get('open', 0)),
                    'high': float(kline.get('high', 0)),
                    'low': float(kline.get('low', 0)),
                    'close': float(kline.get('close', 0)),
                    'volume': float(kline.get('volume', 0))
                })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, 
                                 std_dev: float = 2.0) -> pd.DataFrame:
        """
        计算布林带指标
        
        Args:
            df: 包含价格数据的DataFrame
            period: 移动平均周期 (默认20)
            std_dev: 标准差倍数 (默认2.0)
            
        Returns:
            包含布林带指标的DataFrame
        """
        if df.empty or 'close' not in df.columns:
            print("数据为空或缺少收盘价数据")
            return df
        
        # 计算中轨线 (简单移动平均)
        df['MA'] = df['close'].rolling(window=period).mean()
        
        # 计算标准差
        df['STD'] = df['close'].rolling(window=period).std()
        
        # 计算上轨线和下轨线
        df['Upper_Band'] = df['MA'] + (std_dev * df['STD'])
        df['Lower_Band'] = df['MA'] - (std_dev * df['STD'])
        
        # 计算布林带宽度和位置
        df['BB_Width'] = df['Upper_Band'] - df['Lower_Band']
        df['BB_Position'] = (df['close'] - df['Lower_Band']) / (df['Upper_Band'] - df['Lower_Band'])
        
        print(f"布林带指标计算完成 (周期: {period}, 标准差倍数: {std_dev})")
        return df
    
    def analyze_bollinger_signals(self, df: pd.DataFrame) -> Dict:
        """
        分析布林带信号
        
        Args:
            df: 包含布林带指标的DataFrame
            
        Returns:
            信号分析结果
        """
        if df.empty or 'Upper_Band' not in df.columns:
            return {}
        
        latest = df.iloc[-1]
        recent_data = df.tail(20)  # 最近20个数据点
        
        signals = {
            'current_price': latest['close'],
            'upper_band': latest['Upper_Band'],
            'middle_band': latest['MA'],
            'lower_band': latest['Lower_Band'],
            'bb_position': latest['BB_Position'],
            'bb_width': latest['BB_Width'],
            'signals': []
        }
        
        # 价格位置分析
        if latest['close'] >= latest['Upper_Band']:
            signals['signals'].append("价格触及上轨 - 可能超买")
        elif latest['close'] <= latest['Lower_Band']:
            signals['signals'].append("价格触及下轨 - 可能超卖")
        elif latest['close'] > latest['MA']:
            signals['signals'].append("价格在中轨上方 - 偏多")
        else:
            signals['signals'].append("价格在中轨下方 - 偏空")
        
        # 布林带宽度分析
        avg_width = recent_data['BB_Width'].mean()
        if latest['BB_Width'] < avg_width * 0.8:
            signals['signals'].append("布林带收口 - 可能即将突破")
        elif latest['BB_Width'] > avg_width * 1.2:
            signals['signals'].append("布林带扩张 - 波动性增加")
        
        return signals
    
    def get_available_symbols(self) -> List[str]:
        """
        获取可用的交易对列表
        
        Returns:
            交易对列表
        """
        try:
            url = f"{self.base_url}/api/v1/symbols"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                symbols = [symbol['symbol'] for symbol in data['data']]
            elif isinstance(data, list):
                symbols = [symbol.get('symbol', '') for symbol in data]
            else:
                symbols = []
            
            return symbols
            
        except Exception as e:
            print(f"获取交易对列表失败: {e}")
            return ['ETH-USD', 'BTC-USD', 'SOL-USD']  # 返回一些常见的交易对
    
    def generate_mock_data(self, symbol: str, days: int = 30) -> List[Dict]:
        """
        生成模拟K线数据用于演示
        
        Args:
            symbol: 交易对符号
            days: 生成数据的天数
            
        Returns:
            模拟K线数据列表
        """
        print(f"生成 {symbol} 的模拟K线数据...")
        
        # 基础价格（根据交易对设置不同的起始价格）
        base_prices = {
            'ETH-USD': 3000,
            'BTC-USD': 50000,
            'SOL-USD': 100,
            'default': 1000
        }
        base_price = base_prices.get(symbol, base_prices['default'])
        
        # 生成时间序列（每分钟一个数据点）
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        data = []
        current_price = base_price
        current_time = start_time
        
        # 模拟价格波动
        np.random.seed(42)  # 固定随机种子以便复现
        
        while current_time < end_time:
            # 生成随机价格变动（正态分布）
            price_change = np.random.normal(0, 0.02)  # 2%的标准差
            current_price *= (1 + price_change)
            
            # 确保价格不会变成负数或过小
            if current_price < base_price * 0.1:
                current_price = base_price * 0.1
            elif current_price > base_price * 10:
                current_price = base_price * 10
            
            # 生成OHLCV数据
            open_price = current_price
            high_price = open_price * (1 + abs(np.random.normal(0, 0.01)))
            low_price = open_price * (1 - abs(np.random.normal(0, 0.01)))
            close_price = open_price * (1 + np.random.normal(0, 0.005))
            volume = np.random.uniform(100, 1000)
            
            # 确保OHLC数据的逻辑正确性
            high_price = max(open_price, high_price, close_price)
            low_price = min(open_price, low_price, close_price)
            
            data.append([
                int(current_time.timestamp() * 1000),  # timestamp
                round(open_price, 2),                  # open
                round(high_price, 2),                  # high
                round(low_price, 2),                   # low
                round(close_price, 2),                 # close
                round(volume, 2)                       # volume
            ])
            
            current_price = close_price
            current_time += timedelta(minutes=1)
        
        print(f"生成了 {len(data)} 条模拟K线数据")
        return data


def main():
    """主函数"""
    print("=== Paradex K线数据获取和布林带指标计算 ===")
    
    # 创建分析器实例
    analyzer = ParadexKlineAnalyzer()
    
    # 获取可用交易对
    print("\n正在获取可用交易对...")
    symbols = analyzer.get_available_symbols()
    if symbols:
        print(f"可用交易对: {symbols[:10]}...")  # 显示前10个
    else:
        print("使用默认交易对: ETH-USD")
        symbols = ['ETH-USD']
    
    # 选择交易对
    symbol = symbols[0] if symbols else 'ETH-USD'
    print(f"\n使用交易对: {symbol}")
    
    # 获取过去30天的分钟K线数据
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)
    
    klines = analyzer.get_klines(
        symbol=symbol,
        interval="1m",
        start_time=start_time,
        end_time=end_time,
        limit=10000  # 增加限制以获取更多数据
    )
    
    if not klines:
        print("API获取数据失败，使用模拟数据进行演示...")
        klines = analyzer.generate_mock_data(symbol, days=30)
        
        if not klines:
            print("无法生成模拟数据，程序退出")
            return
    
    # 转换为DataFrame
    df = analyzer.parse_klines_to_dataframe(klines)
    if df.empty:
        print("数据解析失败，程序退出")
        return
    
    print(f"\n数据概览:")
    print(f"数据条数: {len(df)}")
    print(f"时间范围: {df.index.min()} 到 {df.index.max()}")
    print(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
    
    # 计算布林带指标
    df_with_bb = analyzer.calculate_bollinger_bands(df, period=20, std_dev=2.0)
    
    # 分析布林带信号
    signals = analyzer.analyze_bollinger_signals(df_with_bb)
    
    # 显示结果
    print(f"\n=== 布林带指标分析结果 ===")
    print(f"当前价格: {signals.get('current_price', 0):.2f}")
    print(f"上轨: {signals.get('upper_band', 0):.2f}")
    print(f"中轨: {signals.get('middle_band', 0):.2f}")
    print(f"下轨: {signals.get('lower_band', 0):.2f}")
    print(f"布林带位置: {signals.get('bb_position', 0):.2f}")
    print(f"布林带宽度: {signals.get('bb_width', 0):.2f}")
    
    print(f"\n信号分析:")
    for signal in signals.get('signals', []):
        print(f"- {signal}")
    
    # 保存数据到CSV文件
    output_file = f"{symbol.replace('-', '_')}_bollinger_bands.csv"
    df_with_bb.to_csv(output_file)
    print(f"\n数据已保存到: {output_file}")
    
    # 显示最近10条数据
    print(f"\n最近10条数据:")
    recent_data = df_with_bb[['close', 'MA', 'Upper_Band', 'Lower_Band', 'BB_Position']].tail(10)
    print(recent_data.round(4))


if __name__ == '__main__':
    main()
