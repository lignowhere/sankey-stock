"""
Data fetcher module for vnstock integration
Fetches financial data from vnstock and converts it to the format expected by the Sankey generators
"""

import pandas as pd
from vnstock import Vnstock

# Register API key for authenticated access (60 requests/min vs 20 for guests)
# Introduced in vnstock 3.4.0+
try:
    from vnstock import register_user
    register_user(api_key='vnstock_2d2127c3893e9c557e990c5997dee09e')
    print("✅ vnstock (v3.4.1) API key registered successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not register API key: {e}")
    print("Continuing with guest access (20 requests/min limit)")

def fetch_financial_data(symbol, report_type, period, year):
    """
    Fetch financial data from vnstock
    
    Args:
        symbol (str): Stock symbol (e.g., 'VNM', 'VCB')
        report_type (str): Type of report ('balance', 'income', 'cashflow')
        period (str): Period ('Q1', 'Q2', 'Q3', 'Q4', 'year')
        year (int): Year (e.g., 2024)
    
    Returns:
        pandas.DataFrame: Financial data in the format expected by Sankey generators
    """
    try:
        # Initialize vnstock with KBS source (best for detailed financial reports in v3.4.1)
        # KBS returns detailed items according to Circular 200, but limited history (5 periods)
        stock = Vnstock().stock(symbol=symbol.upper(), source='KBS')
        
        # Determine period type (NAM/year/yearly for yearly, otherwise quarter)
        period_lower = period.lower()
        period_type = 'year' if period_lower in ['year', 'nam', 'yearly'] else 'quarter'
        
        # Fetch data. KBS returns "long" format: items as rows, periods as columns
        if report_type.lower() == 'balance':
            df = stock.finance.balance_sheet(period=period_type)
        elif report_type.lower() == 'income':
            df = stock.finance.income_statement(period=period_type)
        elif report_type.lower() == 'cashflow':
            df = stock.finance.cash_flow(period=period_type)
        else:
            raise ValueError(f"Invalid report type: {report_type}")
        
        if df is None or df.empty:
            raise ValueError(f"No data available for {symbol} - {report_type} - {period}")

        # --- Data Mapping Layer for KBS (Long format) ---
        # 1. Selection logic: KBS uses columns like '2024-Q3' or '2024'
        if period_type == 'year':
            target_col = str(year)
        else:
            # Quarter mapping: Q1 -> Q1, etc.
            q_code = period.upper() if 'Q' in period.upper() else f"Q{period}"
            target_col = f"{year}-{q_code}"
            
        if target_col not in df.columns:
            # Fallback: Find the most recent column that starts with the year
            year_cols = [c for c in df.columns if c.startswith(str(year))]
            if year_cols:
                # Sort to get the latest (X-Q4 > X-Q1)
                target_col = sorted(year_cols, reverse=True)[0]
                print(f"⚠️ {target_col} not found exactly. Using {target_col} instead.")
            else:
                # Fallback to the latest available column overall (ignoring metadata)
                meta_cols = ['ticker', 'item', 'item_id', 'Năm', 'Kỳ']
                data_cols = [c for c in df.columns if c not in meta_cols]
                if data_cols:
                    target_col = data_cols[0] # Usually KBS returns latest first
                    print(f"⚠️ Year {year} not found. Using latest available: {target_col}")
                else:
                    raise ValueError(f"No numeric data columns found for {symbol}")

        # 2. Extract 'item' and the target column
        # KBS returns data in THOUSAND VND, so we multiply by 1000 to get VND
        # this ensures compatibility with the extraction modules which expect VND
        transposed = df[['item', target_col]].copy()
        transposed.columns = ['CHỈ TIÊU', 'VALUE']
        transposed['VALUE'] = transposed['VALUE'] * 1000
        
        print(f"✅ Successfully fetched and transformed KBS data for {symbol} ({target_col})")
        return transposed, target_col
                
    except Exception as e:
        print(f"❌ Failed to fetch data for {symbol}: {str(e)}")
        raise Exception(f"Error fetching data from vnstock: {str(e)}")


def fetch_balance_sheet(symbol, period, year):
    """Fetch balance sheet data"""
    return fetch_financial_data(symbol, 'balance', period, year)


def fetch_income_statement(symbol, period, year):
    """Fetch income statement data"""
    return fetch_financial_data(symbol, 'income', period, year)


def fetch_cash_flow(symbol, period, year):
    """Fetch cash flow data"""
    return fetch_financial_data(symbol, 'cashflow', period, year)
