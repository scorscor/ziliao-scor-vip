# 连续上涨策略选股系统

基于连续 N 天小涨模式的股票策略回测工具。

## 策略说明

筛选连续 N 天收盘价上涨，且每天涨幅小于设定阈值的股票，在第 N 天尾盘买入，统计持有不同交易日后的收益表现。

基于 2023 年 00 开头股票回测结果：
- 持有 5 个交易日：平均收益 +0.33%, 胜率 50.69%
- 持有 10 个交易日：平均收益 +0.70%, 胜率 53.58%

## 环境要求

- Python >= 3.9
- pandas
- numpy
- pyarrow
- openpyxl

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 配置参数

编辑 `consecutive_up_strategy.py` 文件顶部的配置项：

```python
# 回测数据文件路径
DATA_FILE = 'daily_fq_20260330.parquet'

# 回测起始日期，格式为 YYYYMMDD
START_DATE = 20230101

# 回测结束日期，格式为 YYYYMMDD
END_DATE = 20231231

# 股票代码前缀，例如 '00'、'60'、'30'
TS_CODE_PREFIX = '00'

# 至少连续上涨多少个交易日才触发信号
MIN_UP_DAYS = 5

# 单日涨幅上限，单位为百分比
MAX_DAILY_GAIN = 5.0

# 收益计算使用的价格列，这里使用后复权收盘价
PRICE_COLUMN = 'close_hfq'

# PE_TTM 过滤条件：
# - 'all': 全部买入（默认）
# - 数字如 10: 只买 pe_ttm 在 1-10 范围的股票
# - 数字如 20: 只买 pe_ttm 在 1-20 范围的股票
# - -1: 只买 pe_ttm <= 0 的股票
PE_TTM_FILTER = 'all'

# 需要统计的持有周期，单位为交易日
HOLD_TRADE_DAYS = list(range(1, 16))

# 个股表现榜单显示的数量
TOP_N = 10

# 个股表现榜单按持有多少个交易日的收益排序
TOP_STOCK_HOLD_DAY = 5

# 导出 Excel 文件名前缀
EXPORT_FILE_PREFIX = 'consecutive_up_strategy_report'
```

### 2. 运行策略

```bash
python consecutive_up_strategy.py
```

## 输出说明

### 控制台输出

程序运行后会在控制台输出：
- 持有期收益统计（平均收益、中位数、胜率、样本数）
- 按买入月份统计的月均收益
- 收益分布统计（最大值、最小值、标准差）
- 信号日特征（第 N 天平均涨幅、累计涨幅）
- 个股表现 Top N 榜单

### Excel 导出文件

生成包含三个 Sheet 的 Excel 文件：

1. **平均收益** - 不同持有周期的收益汇总
2. **月份统计** - 按买入月份的收益统计
3. **每笔明细** - 每笔交易的详细信息

## 数据格式

需要 `.parquet` 格式的回测数据文件，包含以下必要字段：

| 字段 | 说明 |
|------|------|
| ts_code | 股票代码 |
| trade_date | 交易日期 |
| close_hfq | 后复权收盘价 |
| close | 原始收盘价 |
| pre_close | 前收盘价 |
| pct_chg | 涨跌幅 |
| pe_ttm | 市盈率 TTM |

## 许可证

MIT License
