import json
from datetime import datetime

def format_market_data(watchlist_overview):
    """
    Format market data for the AI prompt, similar to the 'Alpha Arena' style.
    """
    output = []
    output.append("### CURRENT MARKET STATE FOR WATCHLIST\n")

    for symbol, data in watchlist_overview.items():
        price = data.get('price', 0)
        rsi = data.get('rsi', 'N/A')
        vwap = data.get('vwap', 'N/A')
        # Format strings for technicals
        if isinstance(rsi, (int, float)):
            rsi_str = f"{rsi:.2f}"
        else:
            rsi_str = str(rsi)
            
        if isinstance(vwap, (int, float)):
            vwap_str = f"{vwap:.2f}"
        else:
            vwap_str = str(vwap)

        output.append(f"**{symbol}**")
        output.append(f"Current Price: {price}")
        output.append(f"RSI (14): {rsi_str}")
        output.append(f"VWAP: {vwap_str}")
        
        # Add SMA if available
        if 'sma_200' in data:
            output.append(f"SMA 200: {data['sma_200']:.2f}")
        if 'sma_50' in data:
            output.append(f"SMA 50: {data['sma_50']:.2f}")
            
        output.append("---")
    
    return "\n".join(output)

def format_account_info(account_info):
    """
    Format account information.
    """
    output = []
    output.append("### ACCOUNT INFORMATION & PERFORMANCE\n")
    
    buying_power = account_info.get('buying_power', 0)
    portfolio_value = account_info.get('portfolio_value', 0)
    cash = account_info.get('portfolio_cash', 0)
    
    output.append(f"**Current Account Value:** {portfolio_value:.2f}")
    output.append(f"Available Cash/Buying Power: {buying_power:.2f}")
    output.append(f"Portfolio Cash: {cash:.2f}")
    
    return "\n".join(output)

def format_positions(portfolio_stocks):
    """
    Format current positions.
    """
    output = []
    output.append("### CURRENT POSITIONS\n")
    
    if not portfolio_stocks:
        output.append("No active positions.")
    else:
        for symbol, pos in portfolio_stocks.items():
            qty = pos.get('quantity', 0)
            avg_price = pos.get('average_buy_price', 0)
            current_price = pos.get('price', 0)
            equity = pos.get('equity', 0)
            
            # Calculate unrealized PnL
            unrealized_pnl = equity - (qty * avg_price)
            pnl_pct = (unrealized_pnl / (qty * avg_price)) * 100 if (qty * avg_price) != 0 else 0
            
            output.append(f"**{symbol}**")
            output.append(f"Quantity: {qty}")
            output.append(f"Entry Price: {avg_price:.2f}")
            output.append(f"Current Price: {current_price:.2f}")
            output.append(f"Unrealized PnL: {unrealized_pnl:.2f} ({pnl_pct:.2f}%)")
            output.append("---")
            
    return "\n".join(output)

def compile_prompt_data(account_info, portfolio_stocks, watchlist_overview):
    """
    Compile all sections into the final data string for the prompt.
    """
    sections = []
    
    # 1. Market Data (Context)
    sections.append(format_market_data(watchlist_overview))
    sections.append("\n")
    
    # 2. Account Info
    sections.append(format_account_info(account_info))
    sections.append("\n")
    
    # 3. Positions
    sections.append(format_positions(portfolio_stocks))
    
    return "\n".join(sections)
