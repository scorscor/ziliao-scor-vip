#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连续 5 天小涨策略选股脚本 - 优化版

策略说明:
- 筛选连续 5 天收盘价上涨，且每天涨幅小于 5% 的股票
- 在第 5 天尾盘买入
- 默认展示持有 1-15 个交易日的逐日结果

基于 2023 年 00 开头股票回测结果:
- 持有 5 个交易日：平均收益 +0.33%, 胜率 50.69%
- 持有 10 个交易日：平均收益 +0.70%, 胜率 53.58%
"""

import pandas as pd
import numpy as np
import warnings
import time
from pathlib import Path
warnings.filterwarnings('ignore')

# 可配置参数
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
# PE_TTM 过滤条件：'all' 表示全部买；1-20 表示只买 pe_ttm 在 1-20 范围的；-1 表示买 pe_ttm <= 0 的
PE_TTM_FILTER = 'all'
# 需要统计的持有周期，单位为交易日
HOLD_TRADE_DAYS = list(range(1, 16))
# 个股表现榜单显示的数量
TOP_N = 10
# 个股表现榜单按持有多少个交易日的收益排序
TOP_STOCK_HOLD_DAY = 5
# 导出 Excel 文件名前缀；实际文件名会自动附带开始和结束日期
EXPORT_FILE_PREFIX = 'consecutive_up_strategy_report'

# 读取 parquet 时保留的必要字段
REQUIRED_COLUMNS = ['ts_code', 'trade_date', PRICE_COLUMN, 'close', 'pre_close', 'pct_chg', 'pe_ttm']


def load_data(file_path: str) -> pd.DataFrame:
    """加载策略所需字段，减少 IO 和内存占用。"""
    print(f"Loading data from {file_path}...")
    df = pd.read_parquet(file_path, engine='pyarrow', columns=REQUIRED_COLUMNS)
    df['trade_date_int'] = df['trade_date'].astype(int)
    return df


def prepare_data(df: pd.DataFrame, ts_code_prefix: str = '00') -> pd.DataFrame:
    """预处理数据：过滤股票范围、排序，并去掉重复交易日记录。"""
    df_prepared = df[df['ts_code'].str.startswith(ts_code_prefix)].copy()
    raw_rows = len(df_prepared)

    df_prepared = df_prepared.sort_values(
        ['ts_code', 'trade_date_int'],
        kind='mergesort'
    ).drop_duplicates(
        subset=['ts_code', 'trade_date_int'],
        keep='last'
    ).reset_index(drop=True)

    duplicate_rows = raw_rows - len(df_prepared)
    if duplicate_rows > 0:
        print(f"Removed {duplicate_rows} duplicate rows based on ts_code + trade_date.")

    return df_prepared


def filter_stocks_fast(df: pd.DataFrame,
                       start_date: int,
                       end_date: int,
                       min_up_days: int = 5,
                       max_daily_gain: float = 5.0,
                       pe_ttm_filter = 'all') -> tuple:
    """
    筛选股票信号。
    pe_ttm_filter: 'all' 表示全部买；数字如 10 表示只买 pe_ttm 在 0-10 范围的；-1 表示买 pe_ttm <= 0 的
    """
    # 筛选日期区间
    df_filtered = df[(df['trade_date_int'] >= start_date) &
                     (df['trade_date_int'] <= end_date)].copy()

    # 应用 PE_TTM 过滤
    if pe_ttm_filter != 'all':
        pe_val = int(pe_ttm_filter)
        if pe_val == -1:
            # 买 pe_ttm <= 0 的
            df_filtered = df_filtered[df_filtered['pe_ttm'] <= 0]
        else:
            # 买 pe_ttm 在 (0, pe_val] 范围的
            df_filtered = df_filtered[(df_filtered['pe_ttm'] > 0) & (df_filtered['pe_ttm'] <= pe_val)]

    # 标记每日是否上涨且涨幅小于限制
    is_up_small = (df_filtered['pct_chg'] > 0) & (df_filtered['pct_chg'] < max_daily_gain)

    # 当前行是新连续段起点：股票切换，或上一交易日不满足条件。
    streak_start = df_filtered['ts_code'].ne(df_filtered['ts_code'].shift()) | (~is_up_small.shift(fill_value=False))
    streak_id = streak_start.cumsum()
    consecutive = np.where(
        is_up_small,
        df_filtered.groupby(streak_id).cumcount().to_numpy() + 1,
        0
    )
    df_filtered['consecutive'] = consecutive.astype(int)

    # 获取信号日数据
    df_signal = df_filtered[df_filtered['consecutive'] >= min_up_days].copy()

    return df_signal, df_filtered


def calculate_returns_vectorized(df_signal: pd.DataFrame,
                                  df_all: pd.DataFrame,
                                  hold_trade_days: list) -> pd.DataFrame:
    """
    计算持有 N 个交易日后的收益。
    """
    df_signal = df_signal.copy()
    df_signal = df_signal.reset_index(drop=True)

    df_all_sorted = df_all.copy()

    # 预先计算所有持有交易日的未来价格。
    for n in hold_trade_days:
        df_all_sorted[f'close_{n}d_later'] = df_all_sorted.groupby('ts_code', sort=False)[PRICE_COLUMN].shift(-n)

    join_cols = ['ts_code', 'trade_date_int'] + [f'close_{n}d_later' for n in hold_trade_days]
    df_signal = df_signal.merge(
        df_all_sorted[join_cols],
        on=['ts_code', 'trade_date_int'],
        how='left',
        validate='one_to_one'
    )

    # 计算收益
    for n in hold_trade_days:
        df_signal[f'ret_{n}d'] = (df_signal[f'close_{n}d_later'] - df_signal[PRICE_COLUMN]) / df_signal[PRICE_COLUMN] * 100
        df_signal[f'close_{n}d'] = df_signal[f'close_{n}d_later']
        df_signal = df_signal.drop(columns=[f'close_{n}d_later'])

    return df_signal


def build_average_returns_summary(df_signal: pd.DataFrame, hold_trade_days: list) -> pd.DataFrame:
    """构建持有期平均收益汇总表。"""
    rows = []
    for n in hold_trade_days:
        valid_ret = df_signal[f'ret_{n}d'].dropna()
        if len(valid_ret) == 0:
            continue
        rows.append({
            '持有交易日数': n,
            '平均收益%': round(valid_ret.mean(), 3),
            '中位数%': round(valid_ret.median(), 3),
            '胜率%': round((valid_ret > 0).sum() / len(valid_ret) * 100, 2),
            '样本数': len(valid_ret),
        })
    return pd.DataFrame(rows)


def build_monthly_summary(df_signal: pd.DataFrame, hold_trade_days: list) -> pd.DataFrame:
    """按买入月份构建平均收益汇总表。"""
    df_monthly = df_signal.copy()
    df_monthly['buy_month'] = (df_monthly['trade_date_int'] // 100).astype(str)
    df_monthly['buy_month'] = df_monthly['buy_month'].str.slice(0, 4) + '-' + df_monthly['buy_month'].str.slice(4, 6)

    monthly_summary = df_monthly.groupby('buy_month').size().to_frame('买入信号数')
    monthly_avg_returns = df_monthly.groupby('buy_month')[[f'ret_{n}d' for n in hold_trade_days]].mean()
    monthly_avg_returns.columns = [f'{n}日平均收益%' for n in hold_trade_days]
    monthly_summary = monthly_summary.join(monthly_avg_returns).round(3).reset_index()
    monthly_summary = monthly_summary.rename(columns={'buy_month': '买入月份'})
    return monthly_summary


def build_trade_details(df_signal: pd.DataFrame, hold_trade_days: list) -> pd.DataFrame:
    """构建每笔交易明细表。"""
    df_details = df_signal.copy()
    df_details['buy_date'] = pd.to_datetime(df_details['trade_date_int'].astype(str), format='%Y%m%d')
    df_details['buy_month'] = df_details['buy_date'].dt.strftime('%Y-%m')

    base_cols = ['ts_code', 'trade_date_int', 'buy_date', 'buy_month', PRICE_COLUMN, 'close', 'pre_close', 'pct_chg', 'consecutive']
    close_cols = [f'close_{n}d' for n in hold_trade_days]
    ret_cols = [f'ret_{n}d' for n in hold_trade_days]
    ordered_cols = base_cols + close_cols + ret_cols

    df_details = df_details[ordered_cols].copy()
    df_details = df_details.rename(columns={
        'ts_code': '股票代码',
        'trade_date_int': '买入日期',
        'buy_date': '买入日期_日期格式',
        'buy_month': '买入月份',
        PRICE_COLUMN: '买入收盘价(后复权)',
        'close': '买入收盘价(原始)',
        'pre_close': '前收盘价(原始)',
        'pct_chg': '当日涨幅%',
        'consecutive': '连续上涨天数',
    })

    close_rename = {f'close_{n}d': f'持有{n}个交易日后收盘价(后复权)' for n in hold_trade_days}
    ret_rename = {f'ret_{n}d': f'持有{n}个交易日收益%' for n in hold_trade_days}
    df_details = df_details.rename(columns={**close_rename, **ret_rename})
    return df_details


def export_analysis_to_excel(df_signal: pd.DataFrame, hold_trade_days: list, output_file: str) -> str:
    """导出分析结果到 Excel 多 sheet 文件。"""
    output_path = Path(output_file).resolve()
    average_summary = build_average_returns_summary(df_signal, hold_trade_days)
    monthly_summary = build_monthly_summary(df_signal, hold_trade_days)
    trade_details = build_trade_details(df_signal, hold_trade_days)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        average_summary.to_excel(writer, sheet_name='平均收益', index=False)
        monthly_summary.to_excel(writer, sheet_name='月份统计', index=False)
        trade_details.to_excel(writer, sheet_name='每笔明细', index=False)

    return str(output_path)


def build_export_file_name(start_date: int, end_date: int) -> str:
    """根据回测日期范围生成导出文件名。"""
    return f'{EXPORT_FILE_PREFIX}_{start_date}_{end_date}.xlsx'


def print_analysis_report(df_signal: pd.DataFrame,
                          df_all: pd.DataFrame,
                          hold_trade_days: list,
                          top_n: int = TOP_N,
                          top_stock_hold_day: int = TOP_STOCK_HOLD_DAY):
    """
    打印分析报告 - 优化版（移除重复读取文件）
    """
    print("\n" + "="*70)
    print("连续 5 天小涨策略 - 回测分析报告")
    print("="*70)
    print(f"总信号数：{len(df_signal)}")
    print(f"收益计算价格列：{PRICE_COLUMN}")

    # 持有期收益统计
    print("\n" + "-"*70)
    print("持有期收益统计")
    print("-"*70)
    print(f"{'持有交易日数':<12} {'平均收益%':<12} {'中位数%':<12} {'胜率%':<10} {'样本数'}")
    print("-"*70)

    average_summary = build_average_returns_summary(df_signal, hold_trade_days)
    for _, row in average_summary.iterrows():
        print(f"{int(row['持有交易日数']):<12} {row['平均收益%']:<12.3f} {row['中位数%']:<12.3f} {row['胜率%']:<10.2f} {int(row['样本数'])}")

    # 按买入月份统计平均收益，按买入日期所在月份归类，不按卖出日期归类。
    print("\n" + "-"*70)
    print("按买入月份统计月均收益")
    print("-"*70)

    monthly_summary = build_monthly_summary(df_signal, hold_trade_days)
    print(monthly_summary.set_index('买入月份').to_string())

    # 收益分布
    print("\n" + "-"*70)
    print("收益分布统计")
    print("-"*70)

    for n in hold_trade_days:
        valid_ret = df_signal[f'ret_{n}d'].dropna()
        if len(valid_ret) > 0:
            print(f"\n持有{n}个交易日:")
            print(f"  最大值：{valid_ret.max():6.2f}%  最小值：{valid_ret.min():6.2f}%  标准差：{valid_ret.std():5.2f}%")
            print(f"  正收益：{(valid_ret > 0).sum()}  负收益：{(valid_ret < 0).sum()}")

    # 信号日特征
    print("\n" + "-"*70)
    print("信号日特征")
    print("-"*70)
    print(f"第 5 天平均涨幅：{df_signal['pct_chg'].mean():.2f}%")
    print(f"第 5 天中位涨幅：{df_signal['pct_chg'].median():.2f}%")

    # 计算连续上涨阶段的累计涨幅，使用后复权收盘价。
    df_all_with_base = df_all.copy()
    df_all_with_base['base_price_shift'] = df_all_with_base.groupby('ts_code', sort=False)[PRICE_COLUMN].shift(MIN_UP_DAYS)

    df_signal_with_cum = df_signal.merge(
        df_all_with_base[['ts_code', 'trade_date_int', 'base_price_shift']],
        on=['ts_code', 'trade_date_int'],
        how='left',
        validate='one_to_one'
    )
    valid_cum = df_signal_with_cum['base_price_shift'].dropna()
    if len(valid_cum) > 0:
        cum_pct = (df_signal_with_cum[PRICE_COLUMN] - df_signal_with_cum['base_price_shift']) / df_signal_with_cum['base_price_shift'] * 100
        print(f"{MIN_UP_DAYS} 个交易日累计平均涨幅(后复权)：{cum_pct.mean():.2f}%")
        print(f"{MIN_UP_DAYS} 个交易日累计中位涨幅(后复权)：{cum_pct.median():.2f}%")

    # 个股表现
    print("\n" + "-"*70)
    print(f"持有 {top_stock_hold_day} 个交易日 - 个股表现 Top {top_n}")
    print("-"*70)

    stock_ret = df_signal.groupby('ts_code')[f'ret_{top_stock_hold_day}d'].mean().dropna()

    print("\n最佳表现:")
    top_stocks = stock_ret.sort_values(ascending=False).head(top_n)
    for ts_code, ret in top_stocks.items():
        print(f"  {ts_code}: {ret:.2f}%")

    print("\n最差表现:")
    bottom_stocks = stock_ret.sort_values().head(top_n)
    for ts_code, ret in bottom_stocks.items():
        print(f"  {ts_code}: {ret:.2f}%")

    print("\n" + "="*70)


def main():
    """主函数"""
    start_time = time.time()

    if TOP_STOCK_HOLD_DAY not in HOLD_TRADE_DAYS:
        raise ValueError("TOP_STOCK_HOLD_DAY 必须包含在 HOLD_TRADE_DAYS 中。")

    print("="*70)
    print("连续 5 天小涨策略选股系统 - 优化版")
    print("="*70)
    print(f"数据文件：{DATA_FILE}")
    print(f"起始日期：{START_DATE}")
    print(f"结束日期：{END_DATE}")
    print(f"股票代码前缀：{TS_CODE_PREFIX}")
    print(f"连续上涨天数：{MIN_UP_DAYS}")
    print(f"每日最大涨幅：{MAX_DAILY_GAIN}%")
    print(f"收益计算价格列：{PRICE_COLUMN}")
    print(f"PE_TTM 过滤：{PE_TTM_FILTER}")
    print(f"持有周期（交易日）：{HOLD_TRADE_DAYS}")

    # 加载数据
    df = load_data(DATA_FILE)
    df_prepared = prepare_data(df, ts_code_prefix=TS_CODE_PREFIX)

    # 筛选信号
    print(f"\n筛选条件：连续{MIN_UP_DAYS}天上涨，每日涨幅<{MAX_DAILY_GAIN}%, PE_TTM={PE_TTM_FILTER}...")
    df_signal, _ = filter_stocks_fast(
        df_prepared,
        start_date=START_DATE,
        end_date=END_DATE,
        min_up_days=MIN_UP_DAYS,
        max_daily_gain=MAX_DAILY_GAIN,
        pe_ttm_filter=PE_TTM_FILTER
    )

    print(f"找到 {len(df_signal)} 个信号")

    # 计算收益 - 这里的 N 表示 N 个交易日，而非自然日。
    print("计算持有期收益（按交易日）...")
    df_signal = calculate_returns_vectorized(df_signal, df_prepared, hold_trade_days=HOLD_TRADE_DAYS)

    elapsed = time.time() - start_time
    print(f"计算完成，耗时：{elapsed:.2f}秒")

    # 打印分析报告
    print_analysis_report(
        df_signal,
        df_prepared,
        hold_trade_days=HOLD_TRADE_DAYS,
        top_n=TOP_N,
        top_stock_hold_day=TOP_STOCK_HOLD_DAY
    )

    export_file = build_export_file_name(START_DATE, END_DATE)
    output_file = export_analysis_to_excel(df_signal, HOLD_TRADE_DAYS, export_file)
    print(f"导出文件：{output_file}")

    total_elapsed = time.time() - start_time
    print(f"\n总耗时：{total_elapsed:.2f}秒")


if __name__ == '__main__':
    main()
