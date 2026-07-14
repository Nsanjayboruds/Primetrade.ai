import utils.session
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def run_analysis():
    print("Loading data...")
    # 1. Load Data
    hist_df = pd.read_csv('historical_data.csv')
    fg_df = pd.read_csv('fear_greed_index.csv')

    print("Preprocessing dates...")
    # 2. Date Preprocessing
    hist_df['Datetime'] = pd.to_datetime(hist_df['Timestamp IST'], format='%d-%m-%Y %H:%M')
    hist_df['Date'] = hist_df['Datetime'].dt.date
    fg_df['Date'] = pd.to_datetime(fg_df['date']).dt.date

    # 3. Merge Data
    print("Merging data...")
    df = pd.merge(hist_df, fg_df, on='Date', how='left')
    
    # 4. Feature Engineering
    print("Engineering features...")
    # Ensure numeric types
    df['Closed PnL'] = pd.to_numeric(df['Closed PnL'], errors='coerce').fillna(0)
    df['Fee'] = pd.to_numeric(df['Fee'], errors='coerce').fillna(0)
    df['Size USD'] = pd.to_numeric(df['Size USD'], errors='coerce').fillna(0)
    
    # Net PnL per trade
    df['Net PnL'] = df['Closed PnL'] - df['Fee']
    
    # Identify closed trades (where PnL is realized)
    closed_trades = df[df['Closed PnL'] != 0].copy()
    closed_trades['Win'] = closed_trades['Closed PnL'] > 0
    
    print("--- OVERALL METRICS ---")
    total_pnl = df['Closed PnL'].sum()
    total_fee = df['Fee'].sum()
    net_pnl = total_pnl - total_fee
    win_rate = closed_trades['Win'].mean() * 100 if len(closed_trades) > 0 else 0
    total_trades = len(df)
    closed_count = len(closed_trades)
    print(f"Total Trades: {total_trades}")
    print(f"Closed Trades (PnL Realized): {closed_count}")
    print(f"Total Gross PnL: ${total_pnl:,.2f}")
    print(f"Total Fees: ${total_fee:,.2f}")
    print(f"Net PnL: ${net_pnl:,.2f}")
    print(f"Overall Win Rate: {win_rate:.2f}%")

    print("\n--- SENTIMENT BASED PERFORMANCE ---")
    # Group by classification
    if 'classification' in closed_trades.columns:
        sentiment_perf = closed_trades.groupby('classification').agg(
            Trade_Count=('Account', 'count'),
            Win_Rate=('Win', 'mean'),
            Avg_Closed_PnL=('Closed PnL', 'mean'),
            Total_Closed_PnL=('Closed PnL', 'sum'),
            Total_Fee=('Fee', 'sum'),
            Avg_Size_USD=('Size USD', 'mean')
        ).reset_index()
        sentiment_perf['Net_PnL'] = sentiment_perf['Total_Closed_PnL'] - sentiment_perf['Total_Fee']
        sentiment_perf['Win_Rate'] = sentiment_perf['Win_Rate'] * 100
        print(sentiment_perf.to_string(index=False))
        
        # Save to CSV for reporting
        sentiment_perf.to_csv('sentiment_performance.csv', index=False)
        
        # Plotting
        plt.figure(figsize=(10, 6))
        sns.barplot(data=sentiment_perf, x='classification', y='Net_PnL', order=['Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'])
        plt.title('Net PnL by Market Sentiment')
        plt.ylabel('Net PnL (USD)')
        plt.xlabel('Sentiment')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('pnl_by_sentiment.png')
        
        plt.figure(figsize=(10, 6))
        sns.barplot(data=sentiment_perf, x='classification', y='Win_Rate', order=['Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'])
        plt.title('Win Rate by Market Sentiment')
        plt.ylabel('Win Rate (%)')
        plt.xlabel('Sentiment')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('winrate_by_sentiment.png')

    print("\n--- DIRECTIONAL PERFORMANCE (BUY vs SELL) BY SENTIMENT ---")
    dir_sentiment = closed_trades.groupby(['classification', 'Side']).agg(
        Net_PnL=('Closed PnL', lambda x: x.sum() - closed_trades.loc[x.index, 'Fee'].sum()),
        Win_Rate=('Win', 'mean'),
        Count=('Account', 'count')
    ).reset_index()
    dir_sentiment['Win_Rate'] = dir_sentiment['Win_Rate'] * 100
    print(dir_sentiment.to_string(index=False))
    dir_sentiment.to_csv('directional_performance.csv', index=False)

    print("\n--- VALUE CORRELATION ---")
    daily_pnl = df.groupby('Date').agg(
        Daily_Gross_PnL=('Closed PnL', 'sum'),
        Daily_Fee=('Fee', 'sum'),
        Sentiment_Value=('value', 'first') # Take the first sentiment value for that day
    ).reset_index()
    daily_pnl['Daily_Net_PnL'] = daily_pnl['Daily_Gross_PnL'] - daily_pnl['Daily_Fee']
    
    # Drop NaN sentiment values if any
    daily_pnl = daily_pnl.dropna(subset=['Sentiment_Value'])
    if not daily_pnl.empty:
        corr = daily_pnl['Sentiment_Value'].corr(daily_pnl['Daily_Net_PnL'])
        print(f"Correlation between daily Sentiment Value (0-100) and Daily Net PnL: {corr:.4f}")
        
        plt.figure(figsize=(8, 6))
        sns.scatterplot(data=daily_pnl, x='Sentiment_Value', y='Daily_Net_PnL')
        plt.axhline(0, color='red', linestyle='--', alpha=0.5)
        plt.title('Daily Net PnL vs Fear & Greed Index')
        plt.xlabel('Fear & Greed Index (0-100)')
        plt.ylabel('Daily Net PnL (USD)')
        plt.tight_layout()
        plt.savefig('sentiment_correlation.png')

if __name__ == '__main__':
    run_analysis()
