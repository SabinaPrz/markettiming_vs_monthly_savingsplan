__author__ = "Sabina Przioda"
__version__ = "1.0.0"
__maintainer__ = "Sabina Przioda"
__status__ = "Production"

import datetime
from dateutil.relativedelta import relativedelta
import numpy as np

def get_new_xticks_per_year(df):
    """
    Create xticks per year for plotting KPIs from the investment plan of the 20 year horizon.
    
    Parameter:
    df - dataframe with year as column 
    
    Return:
    xticks - x axis ticks one per year
    """
    years = df.groupby('year').Date.first().dt.year.values
    xticks = np.concatenate(([np.datetime64(f'{years[0]-1}-01-01')], df.groupby('year').Date.first().values, [np.datetime64(f'{years[-1]+1}-01-01')], [np.datetime64(f'{years[-1]+2}-01-01')]))
    
    return xticks


def get_start_and_end_of_history(etf_idx, etf_idx_dict):
    """
    Get the start and end date of the ETF index based on values from a dictionary.
    
    Parameter: 
    etf_idx - an ETF index readable for the pandas DataReader
    etf_idx_dict - dictionary containing the start and end dates of the data per index
    
    Return: 
    start_date - start_date of the index
    end_date - end_date of the index
    """
    # start date of data
    if etf_idx in etf_idx_dict.keys():
        start_date = datetime.datetime.strptime(etf_idx_dict[etf_idx], '%Y-%m-%d')
    else:
        start_date = datetime.datetime(1920, 1, 1)
    # end date of data
    end_date = datetime.datetime(2020, 1, 1)
    
    return start_date, end_date

def get_horizon_start_end(start_date, year_start, horizon_length=20, verbose=1):
    """
    Get the start end end date of the e.g. 20 year horizon. By default the horizon_length is 20 years.
    
    Parameter: 
    start_date - datetime start_date of the index
    year_start - int offset in years to the horizon start
    horizon_length - int length of the horizon window. Default is 20 years
    verbose - {0, 1} verbosity. Default is 1
    
    Return: 
    horizon_start - horizon window start
    horizon_end - horizon window end
    """
    horizon_start = start_date + relativedelta(years=year_start)
    horizon_end = horizon_start + relativedelta(years=horizon_length)
    if verbose == 1:
        print(horizon_start, horizon_end)
    return horizon_start, horizon_end

def compute_moving_max(df, window_size=125):
    """
    Computes the moving max over the a window having a size defined by window_size.
    
    Parameters:
    df - Dataframe containing the data from the pandas datareader
    window_size - int window size for computing the maximum in a rolling window fashion
    
    Return:
    df - Dataframe with an additional column called moving_max
    """
    # The rolling moving max is the maximum over a 6 months rolling window
    df['moving_max'] = df.High.rolling(window_size).max()
    # irerate through null values in moving_max (124 values) in reverse order
    for i, (row_idx, row) in enumerate(df[df.moving_max.isnull()][::-1].iterrows()):
        df.loc[row_idx, 'moving_max'] = df[df.moving_max.isnull()].High.max()
        
    return df

def compute_percent_drop(df):
    """
    Calculate the drop of price in percent with respect to the moving_max. The value of the price is Adj Close.
    
    Parameters:
    df - Dataframe containing prices of the ETF
    
    Return: 
    df - Dataframe containing column percent_drop
    """
    df['percent_drop'] = 1 - df['Adj Close'] / df.moving_max
    return df

def assign_available_capital(df, monthly_savings):
    """
    Assign the available capital. It's modeled as getting amount of money specified in monthly_savings each month at the first business day of the month.
    
    Parameters:
    df - Dataframe containing prices of the ETF
    monthly_savings - int the amount of money able to save and invest each month
    
    Return:
    df - Dataframe containing the information about the capital available to invest
    """
    money_input = df.groupby(['year', 'month']).Date.first().to_frame()
    money_input['capital'] = monthly_savings
    df = df.merge(money_input, how='left', on='Date')
    df.capital = df.capital.cumsum().fillna(method='ffill')
    return df

def create_monthly_investment_plan(df, perc_monthly_invest):
    """
    Create the investment plan according to the monthly savings plan. Every first of the month shares are bought at the opening price for the amount of capital available at the time.
    
    Parameters:
    df - Dataframe with all available information about prices, moving_max, percentage_drop
    perc_monthly_invest - [0, 1] percentage of capital to invest on a monthly basis. For the monthly savings plan this is 1.0, for the market timing strategy
                          this is 0.0
    
    Return:
    df - investment plan showing True in the buy column if invested, the amount of investment and the updated cash
    """
    
    try:
        assert perc_monthly_invest >= 0 and perc_monthly_invest <= 1
    except AssertionError as e:
        e.args += (f'perc_monthly_invest must be within [0, 1] but is {perc_monthly_invest}', )
        raise
        
    # buying_time contains all investments at the first business day of the month  
    buying_time = df.groupby(['year', 'month']).Date.first().to_frame()
    buying_time['buy'] = perc_monthly_invest > 0
    buying_time['investment_percent'] = perc_monthly_invest
    buying_time['investment_amount'] = df[df.capital.notnull()].capital.iloc[0]*perc_monthly_invest
    # merge to the investmentplan of no invests the buying_time containing all times something is invested
    df = df.merge(buying_time, how='left', on='Date').fillna(
        {'buy': False, 'investment_percent': 0, 'investment_amount': 0})
    # update the cash
    df['cash'] = df.capital - df.investment_amount.cumsum()  

    return df

def create_drop_threshold_investment_plan(df, mode, perc_drop_threshold, waiting_days, drop_multiplier):
    """
    Create the investment plan according to the market timing strategy. Depending on the perc_drop_thershold if percent_drop is below that threshold, money is invested.
    The percentage of cash invested is determiend by the product of percent_drop and drop_multiplier.
    If the strategy is hybrid it's not possible to invest an additional amount on the same day the monthly savings plan is executed.
    
    Parameters:
    df - Dataframe with all available information about prices, moving_max, percentage_drop
    mode - {monthly_invest_strategy, markettiming_strategy, hybrid_strategy} strategy mode: One of the three investment strategies
    perc_drop_threshold - [0, 1.0] the threshold for percent_drop to trigger a possible buy 
    waiting_days - int > 0 minimum number of days between two buys triggered by the percent_drop
    drop_multiplier - [1, inf) the multiplier for the percent_drop to determine the percentage of cash to invest
    
    Return:
    df - investment plan showing True in the buy column if invested, the amount of investment and the updated cash
    """
    
    try:
        assert (perc_drop_threshold >= 0 and perc_drop_threshold <= 1.0)
    except AssertionError as e:
        e.args += (f'perc_drop_threshold must be within [0, 1.0] but is {perc_drop_threshold}', )
        raise
        
    try:
        assert (waiting_days >= 1 and type(waiting_days)==int)
    except AssertionError as e:
        e.args += (f'waiting_days must be an int but is {waiting_days}', )
        raise
        
    try:
        assert (drop_multiplier >= 1 and type(drop_multiplier)==int) 
    except AssertionError as e:
        e.args += (f'drop_multiplier must be an int but is {drop_multiplier}', )
        raise
    
    # initialize last_buy to be in the past such that it's possible to buy at the first possible time
    last_buy = -waiting_days
    # buying after the last index in the investment_plan is not possible
    last_idx = df.index[-1]
    # determine whether to buy or not buy for each row based on percent_drop (of the previous day) and perc_drop_threshold 
    for i, (row_idx, row) in enumerate(df[df.percent_drop>=perc_drop_threshold].iterrows()):
        if row_idx - last_buy >= waiting_days and row_idx != last_idx:
            # buy on the next day at the opening price
            next_row_idx = row_idx + 1
            # if hybrid_strategy then an investment at the first of the month is not possible, because it's anyway being invested due to the monthly investment
            if mode == 'hybrid_strategy' and df.loc[next_row_idx].buy == True:
                continue
            df.loc[next_row_idx, 'buy'] = True
            last_buy = row_idx
            df.loc[next_row_idx, 'investment_percent'] = np.minimum(1, df.percent_drop.loc[row_idx] * drop_multiplier)
            df.loc[next_row_idx, 'investment_amount'] = df.loc[next_row_idx].cash * df.loc[next_row_idx, 'investment_percent']
            df.loc[next_row_idx:, 'cash'] = df.loc[next_row_idx:].cash - df.loc[next_row_idx].investment_amount 
            
    return df
    
def determine_buy_and_investment_amount(df, mode, perc_monthly_invest, perc_drop_threshold, waiting_days, drop_multiplier):
    """
    Create the investment plan according to one of the three strategies (mode): monthly_invest_strategy|markettiming_strategy|hybrid_strategy.
    The investment plan shows when is being invested and how much is invested.
    
    Parameters:
    df - Dataframe with all available information about prices, moving_max, percentage_drop
    mode - {monthly_invest_strategy, markettiming_strategy, hybrid_strategy} strategy mode: One of the three investment strategies
    perc_monthly_invest - [0, 1] percentage of capital to invest on a monthly basis. For the monthly savings plan this is 1.0, for the market timing strategy
                          this is 0.0
    perc_drop_threshold - [0, 1.0] the threshold for percent_drop to trigger a possible buy 
    waiting_days - [1, inf) minimum number of days between two buys triggered by the percent_drop
    drop_multiplier - [1, inf) the multiplier for the percent_drop to determine the percentage of cash to invest
    
    Return:
    df - investment plan showing True in the buy column if invested, the amount of investment, 
         the updated cash and the share amount bought at that point in time
    """
    
    modes = ['monthly_invest_strategy', 'markettiming_strategy', 'hybrid_strategy']
    try:
        assert mode in modes
    except AssertionError as e:
        e.args += (f'mode must be one of the values {modes} but is {mode}', )
        raise
        
    if mode == 'monthly_invest_strategy':
        perc_monthly_invest = 1.0
    elif mode == 'markettiming_strategy':
        perc_monthly_invest = 0.0
        
    if perc_monthly_invest == 1.0:
        df = create_monthly_investment_plan(df, perc_monthly_invest)
    else:
        df = create_monthly_investment_plan(df, perc_monthly_invest)
        df = create_drop_threshold_investment_plan(df, mode, perc_drop_threshold, waiting_days, drop_multiplier)
        
    df['investment_percent'] = df.investment_percent.fillna(0)
    df['investment_amount'] = df.investment_amount.fillna(0)
    df['share_amount'] = df.investment_amount/df.Open
    
    return df

def create_investment_plan(df, start_date, year_start, horizon_length, mode, monthly_savings, verbose=1, perc_monthly_invest=0.9, perc_drop_threshold=0.035, 
                           waiting_days=3, drop_multiplier=9): 
    """
    Create the investment plan starting from the dataframe from pandas datareader. 
    Depending on the strategy an investment plan is created. The investment strategy is defined in mode which can take the options
    monthly_invest_strategy|markettiming_strategy|hybrid_strategy. 
    In detail those strategies are:
    monthly_invest_strategy: Every first of the month shares are bought at the opening price for the amount of capital available at the time.
    markettiming_strategy: Depending on the perc_drop_thershold if percent_drop is below that threshold, money is invested.
                       The percentage of cash invested is determined by the product of percent_drop and drop_multiplier.
                       Between two investments there must be at least number of of waiting_days. 
    hybrid_strategy: Hybrid between monthly savings plan and market timing strategy. 
                     Every first of the month a percentage defined in perc_monthly_invest of the monthly capital is invested.
                     The rest is left as cash and can be invested depending on the perc_drop_threshold and waiting_days.
                     
    Parameters:
    df - Dataframe containing the data from the pandas datareader
    start_date - datetime start_date of the index
    year_start - int offset in years to the horizon start
    horizon_length - int length of the horizon window. Default is 20 years
    mode - {monthly_invest_strategy, markettiming_strategy, hybrid_strategy} strategy mode: One of the three investment strategies
    monthly_savings - int the amount of money able to save and invest each month
    verbose - {0, 1} verbosity. Default is 1
    perc_monthly_invest - [0, 1] percentage of capital to invest on a monthly basis. For the monthly savings plan this is 1.0, for the market timing strategy
                          this is 0.0
    perc_drop_threshold - [0, 1.0] the threshold for percent_drop to trigger a possible buy 
    waiting_days - [1, inf) minimum number of days between two buys triggered by the percent_drop
    drop_multiplier - [1, inf) the multiplier for the percent_drop to determine the percentage of cash to invest
    
    Return:
    investment_plan - investment plan showing True in the buy column if invested, the amount of investment, 
                      the updated cash and the share amount bought at that point in time
    """
    horizon_start, horizon_end = get_horizon_start_end(start_date, year_start, horizon_length, verbose)
    df_horizon = df.loc[horizon_start:horizon_end].reset_index()
    df_horizon = compute_percent_drop(df_horizon)
    investment_plan = assign_available_capital(df_horizon, monthly_savings)
    investment_plan = determine_buy_and_investment_amount(investment_plan, mode, perc_monthly_invest, perc_drop_threshold, waiting_days, drop_multiplier)
    
    return investment_plan

def compute_roi(investment_plan):
    """
    Compute the return of invest per year in the investment horizon.
    
    Parameters: 
    investment_plan - complete investment plan as computed by determine_buy_and_investment_amount
    
    Return:
    portfolio_per_year - the net worth of the portfolio per year
    amount_invested_per_year - the amoung invested per year
    win_per_year - the difference between portfolio and amount invested per year
    roi_per_year - the return of invest per year in percent
    """
    portfolio_per_year = investment_plan.groupby('year').share_amount.sum().cumsum()*investment_plan.groupby('year').Open.tail(1).values
    amount_invested_per_year = investment_plan.groupby('year').investment_amount.sum().cumsum()
    win_per_year = portfolio_per_year - amount_invested_per_year
    roi_per_year = win_per_year/amount_invested_per_year
    
    return portfolio_per_year, amount_invested_per_year, win_per_year, roi_per_year