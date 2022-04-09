

import warnings

warnings.filterwarnings("ignore")

import pandas as pd
from IPython import display

display.set_matplotlib_formats("svg")

from finrl_meta import config
from main import check_and_make_directories
from finrl_meta.data_processors.tushare import Tushare, ReturnPlotter
from finrl_meta.env_stock_trading.env_stocktrading_China_A_shares import StockTradingEnv
from agents.stablebaselines3_models import DRLAgent
import os
from typing import List
from argparse import ArgumentParser
from finrl_meta import config
from finrl_meta.config_tickers import DOW_30_TICKER
from finrl_meta.config import (
    DATA_SAVE_DIR,
    TRAINED_MODEL_DIR,
    TENSORBOARD_LOG_DIR,
    RESULTS_DIR,
    INDICATORS,
    TRAIN_START_DATE,
    TRAIN_END_DATE,
    TEST_START_DATE,
    TEST_END_DATE,
    TRADE_START_DATE,
    TRADE_END_DATE,
    ERL_PARAMS,
    RLlib_PARAMS,
    SAC_PARAMS,
    ALPACA_API_KEY,
    ALPACA_API_SECRET,
    ALPACA_API_BASE_URL,
)

pd.options.display.max_columns = None

print("ALL Modules have been imported!")


# %% md

### Create folders

# %%

import os

'''
use check_and_make_directories() to replace the following

if not os.path.exists("./datasets"):
    os.makedirs("./datasets")
if not os.path.exists("./trained_models"):
    os.makedirs("./trained_models")
if not os.path.exists("./tensorboard_log"):
    os.makedirs("./tensorboard_log")
if not os.path.exists("./results"):
    os.makedirs("./results")
'''

check_and_make_directories([DATA_SAVE_DIR, TRAINED_MODEL_DIR, TENSORBOARD_LOG_DIR, RESULTS_DIR])



# %% md

### Download data, cleaning and feature engineering

# %%

ticket_list = ['600000.SH', '600009.SH', '600016.SH', '600028.SH', '600030.SH',
               '600031.SH', '600036.SH', '600050.SH', '600104.SH', '600196.SH',
               '600276.SH', '600309.SH', '600519.SH', '600547.SH', '600570.SH']

train_start_date = '2015-01-01'
train_stop_date = '2019-08-01'
val_start_date = '2019-08-01'
val_stop_date = '2021-01-03'

token = '27080ec403c0218f96f388bca1b1d85329d563c91a43672239619ef5'

# %%

# download and clean
ts_processor = Tushare(data_source="tushare",
                       start_date=train_start_date,
                       end_date=val_stop_date,
                       time_interval="1d",
                       token=token)
ts_processor.download_data(ticker_list=ticket_list)

# %%

ts_processor.clean_data()
ts_processor.dataframe

# %%

# add_technical_indicator
ts_processor.add_technical_indicator(config.INDICATORS)
ts_processor.clean_data()
ts_processor.dataframe

# %% md

### Split traning dataset

# %%

train = ts_processor.data_split(ts_processor.dataframe, train_start_date, train_stop_date)
len(train.tic.unique())

# %%

train.tic.unique()

# %%

train.head()

# %%

train.shape

# %%

stock_dimension = len(train.tic.unique())
state_space = stock_dimension * (len(config.INDICATORS) + 2) + 1
print(f"Stock Dimension: {stock_dimension}, State Space: {state_space}")

# %% md

### Train

# %%

env_kwargs = {
    "stock_dim": stock_dimension,
    "hmax": 1000,
    "initial_amount": 1000000,
    "buy_cost_pct": 6.87e-5,
    "sell_cost_pct": 1.0687e-3,
    "reward_scaling": 1e-4,
    "state_space": state_space,
    "action_space": stock_dimension,
    "tech_indicator_list": config.INDICATORS,
    "print_verbosity": 1,
    "initial_buy": True,
    "hundred_each_trade": True
}

e_train_gym = StockTradingEnv(df=train, **env_kwargs)

# %% md

## DDPG

# %%

env_train, _ = e_train_gym.get_sb_env()
print(type(env_train))

# %%

agent = DRLAgent(env=env_train)
DDPG_PARAMS = {
    "batch_size": 256,
    "buffer_size": 50000,
    "learning_rate": 0.0005,
    "action_noise": "normal",
}
POLICY_KWARGS = dict(net_arch=dict(pi=[64, 64], qf=[400, 300]))
model_ddpg = agent.get_model("ddpg", model_kwargs=DDPG_PARAMS, policy_kwargs=POLICY_KWARGS)

# %%

trained_ddpg = agent.train_model(model=model_ddpg,
                                 tb_log_name='ddpg',
                                 total_timesteps=10000)

# %% md

## A2C

# %%

agent = DRLAgent(env=env_train)
model_a2c = agent.get_model("a2c")

# %%

trained_a2c = agent.train_model(model=model_a2c,
                                tb_log_name='a2c',
                                total_timesteps=50000)

# %% md

### Trade

# %%

trade = ts_processor.data_split(ts_processor.dataframe, val_start_date, val_stop_date)
env_kwargs = {
    "stock_dim": stock_dimension,
    "hmax": 1000,
    "initial_amount": 1000000,
    "buy_cost_pct": 6.87e-5,
    "sell_cost_pct": 1.0687e-3,
    "reward_scaling": 1e-4,
    "state_space": state_space,
    "action_space": stock_dimension,
    "tech_indicator_list": config.INDICATORS,
    "print_verbosity": 1,
    "initial_buy": False,
    "hundred_each_trade": True
}
e_trade_gym = StockTradingEnv(df=trade, **env_kwargs)

# %%

df_account_value, df_actions = DRLAgent.DRL_prediction(model=trained_ddpg,
                                                       environment=e_trade_gym)

# %%

df_actions.to_csv("action.csv", index=False)
df_actions

# %% md

### Backtest

# %%

# %matplotlib inline
plotter = ReturnPlotter(df_account_value, trade, val_start_date, val_stop_date)
# plotter.plot_all()

# %%

% matplotlib
inline
plotter.plot()

# %%

# %matplotlib inline
# # ticket: SSE 50：000016
# plotter.plot("000016")

# %% md

#### Use pyfolio

# %%

# CSI 300
baseline_df = plotter.get_baseline("399300")

# %%

import pyfolio
from pyfolio import timeseries

daily_return = plotter.get_return(df_account_value)
daily_return_base = plotter.get_return(baseline_df, value_col_name="close")

perf_func = timeseries.perf_stats
perf_stats_all = perf_func(returns=daily_return,
                           factor_returns=daily_return_base,
                           positions=None, transactions=None, turnover_denom="AGB")
print("==============DRL Strategy Stats===========")
perf_stats_all

# %%

import pyfolio
from pyfolio import timeseries

daily_return = plotter.get_return(df_account_value)
daily_return_base = plotter.get_return(baseline_df, value_col_name="close")

perf_func = timeseries.perf_stats
perf_stats_all = perf_func(returns=daily_return_base,
                           factor_returns=daily_return_base,
                           positions=None, transactions=None, turnover_denom="AGB")
print("==============Baseline Strategy Stats===========")
perf_stats_all

# %%

# with pyfolio.plotting.plotting_context(font_scale=1.1):
#         pyfolio.create_full_tear_sheet(returns = daily_return,
#                                        benchmark_rets = daily_return_base, set_context=False)

# %% md

### Authors
github
username: oliverwang15, eitin - infant
