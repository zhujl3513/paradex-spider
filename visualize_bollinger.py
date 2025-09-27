import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.rc("font",family='YouYuan')


def plot_bollinger_bands(csv_file: str, symbol: str = "ETH-USD", days: int = 7):
    """
    绘制布林带指标图表
    
    Args:
        csv_file: CSV文件路径
        symbol: 交易对符号
        days: 显示最近几天的数据
    """
    # 读取数据
    df = pd.read_csv(csv_file, index_col='datetime', parse_dates=True)
    
    # 获取最近N天的数据
    recent_data = df.tail(days * 24 * 60)  # 假设是分钟数据
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    # 绘制价格和布林带
    ax1.plot(recent_data.index, recent_data['close'], label='收盘价', linewidth=1, color='blue')
    ax1.plot(recent_data.index, recent_data['MA'], label='中轨 (MA20)', linewidth=1, color='orange')
    ax1.fill_between(recent_data.index, 
                     recent_data['Upper_Band'], 
                     recent_data['Lower_Band'], 
                     alpha=0.2, color='gray', label='布林带区间')
    ax1.plot(recent_data.index, recent_data['Upper_Band'], '--', color='red', linewidth=1, label='上轨')
    ax1.plot(recent_data.index, recent_data['Lower_Band'], '--', color='green', linewidth=1, label='下轨')
    
    ax1.set_title(f'{symbol} 布林带指标 - 最近{days}天', fontsize=16, fontweight='bold')
    ax1.set_ylabel('价格 (USD)', fontsize=12)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 绘制布林带位置
    ax2.plot(recent_data.index, recent_data['BB_Position'], label='布林带位置', color='purple', linewidth=1)
    ax2.axhline(y=0.8, color='red', linestyle='--', alpha=0.7, label='超买线 (0.8)')
    ax2.axhline(y=0.2, color='green', linestyle='--', alpha=0.7, label='超卖线 (0.2)')
    ax2.axhline(y=0.5, color='gray', linestyle='-', alpha=0.5, label='中位线 (0.5)')
    ax2.fill_between(recent_data.index, 0, 1, alpha=0.1, color='gray')
    
    ax2.set_ylabel('布林带位置', fontsize=12)
    ax2.set_xlabel('时间', fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)
    
    # 格式化x轴
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 保存图表
    output_file = f"{symbol.replace('-', '_')}_bollinger_chart.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")
    
    # 显示图表
    plt.show()

def analyze_signals(csv_file: str, symbol: str = "ETH-USD"):
    """
    分析布林带信号
    
    Args:
        csv_file: CSV文件路径
        symbol: 交易对符号
    """
    df = pd.read_csv(csv_file, index_col='datetime', parse_dates=True)
    
    # 获取有效数据（有布林带指标的数据）
    valid_data = df.dropna(subset=['MA', 'Upper_Band', 'Lower_Band'])
    
    if valid_data.empty:
        print("没有有效的布林带数据")
        return
    
    print(f"\n=== {symbol} 布林带信号分析 ===")
    print(f"分析数据点: {len(valid_data)}")
    print(f"时间范围: {valid_data.index.min()} 到 {valid_data.index.max()}")
    
    # 统计信号
    signals = {
        '触及上轨': (valid_data['close'] >= valid_data['Upper_Band']).sum(),
        '触及下轨': (valid_data['close'] <= valid_data['Lower_Band']).sum(),
        '中轨上方': (valid_data['close'] > valid_data['MA']).sum(),
        '中轨下方': (valid_data['close'] < valid_data['MA']).sum(),
    }
    
    print(f"\n信号统计:")
    for signal, count in signals.items():
        percentage = count / len(valid_data) * 100
        print(f"{signal}: {count} 次 ({percentage:.1f}%)")
    
    # 布林带宽度分析
    avg_width = valid_data['BB_Width'].mean()
    narrow_bands = (valid_data['BB_Width'] < avg_width * 0.8).sum()
    wide_bands = (valid_data['BB_Width'] > avg_width * 1.2).sum()
    
    print(f"\n布林带宽度分析:")
    print(f"平均宽度: {avg_width:.2f}")
    print(f"收口次数: {narrow_bands} ({narrow_bands/len(valid_data)*100:.1f}%)")
    print(f"扩张次数: {wide_bands} ({wide_bands/len(valid_data)*100:.1f}%)")
    
    # 最新信号
    latest = valid_data.iloc[-1]
    print(f"\n最新信号:")
    print(f"当前价格: {latest['close']:.2f}")
    print(f"上轨: {latest['Upper_Band']:.2f}")
    print(f"中轨: {latest['MA']:.2f}")
    print(f"下轨: {latest['Lower_Band']:.2f}")
    print(f"布林带位置: {latest['BB_Position']:.2f}")
    
    if latest['close'] >= latest['Upper_Band']:
        print("🔴 价格触及上轨 - 可能超买")
    elif latest['close'] <= latest['Lower_Band']:
        print("🟢 价格触及下轨 - 可能超卖")
    elif latest['close'] > latest['MA']:
        print("🟡 价格在中轨上方 - 偏多")
    else:
        print("🟠 价格在中轨下方 - 偏空")

if __name__ == "__main__":
    # 检查是否有CSV文件
    import glob
    csv_files = glob.glob("*_bollinger_bands.csv")
    
    if not csv_files:
        print("未找到布林带数据文件，请先运行 main.py")
        exit(1)
    
    csv_file = csv_files[0]
    symbol = csv_file.replace('_bollinger_bands.csv', '').replace('_', '-')
    
    print(f"分析文件: {csv_file}")
    print(f"交易对: {symbol}")
    
    # 分析信号
    analyze_signals(csv_file, symbol)
    
    # 绘制图表
    try:
        plot_bollinger_bands(csv_file, symbol, days=3)
    except ImportError:
        print("\n需要安装matplotlib来绘制图表:")
        print("pip install matplotlib")
    except Exception as e:
        print(f"\n绘制图表时出错: {e}")
