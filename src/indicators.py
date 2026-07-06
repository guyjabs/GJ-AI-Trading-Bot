"""
Canonical Technical Indicator Library.

All indicator calculations live here. Every module in the project
should import from this file instead of computing indicators inline.
Functions accept pandas Series / DataFrames and return pandas objects.
"""

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────
#  Moving Averages
# ──────────────────────────────────────────────

def compute_sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


# ──────────────────────────────────────────────
#  RSI (Wilder's Smoothing)
# ──────────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index using Wilder's smoothing method.
    Returns a Series of RSI values (0-100).
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing (EMA with alpha = 1/period)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ──────────────────────────────────────────────
#  MACD
# ──────────────────────────────────────────────

def compute_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence.
    Returns DataFrame with columns: macd, signal, histogram.
    """
    ema_fast = compute_ema(series, fast)
    ema_slow = compute_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    })


# ──────────────────────────────────────────────
#  Bollinger Bands
# ──────────────────────────────────────────────

def compute_bollinger_bands(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """
    Bollinger Bands.
    Returns DataFrame with columns: upper, middle, lower, width, pct_b.
    pct_b = (price - lower) / (upper - lower) — position within bands (0-1).
    width = (upper - lower) / middle — band width as fraction of middle band.
    """
    middle = compute_sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    band_range = upper - lower
    width = band_range / middle.replace(0, np.nan)
    pct_b = (series - lower) / band_range.replace(0, np.nan)
    return pd.DataFrame({
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "width": width,
        "pct_b": pct_b,
    })


# ──────────────────────────────────────────────
#  ATR (Average True Range)
# ──────────────────────────────────────────────

def compute_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """
    Average True Range — volatility measure.
    Uses Wilder's smoothing.
    """
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return atr


# ──────────────────────────────────────────────
#  ADX (Average Directional Index)
# ──────────────────────────────────────────────

def compute_adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.DataFrame:
    """
    Average Directional Index — trend strength indicator.
    Returns DataFrame with columns: adx, plus_di, minus_di.
    ADX > 25 indicates a strong trend.
    """
    # Directional movement
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

    atr = compute_atr(high, low, close, period)

    # Smoothed DM
    plus_dm_smooth = plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    plus_di = 100 * plus_dm_smooth / atr.replace(0, np.nan)
    minus_di = 100 * minus_dm_smooth / atr.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    return pd.DataFrame({
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di,
    })


# ──────────────────────────────────────────────
#  Stochastic Oscillator
# ──────────────────────────────────────────────

def compute_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    """
    Stochastic Oscillator.
    Returns DataFrame with columns: k (fast), d (slow/signal).
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    denom = (highest_high - lowest_low).replace(0, np.nan)
    k = 100 * (close - lowest_low) / denom
    d = compute_sma(k, d_period)
    return pd.DataFrame({"k": k, "d": d})


# ──────────────────────────────────────────────
#  OBV (On-Balance Volume)
# ──────────────────────────────────────────────

def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On-Balance Volume — cumulative volume flow indicator.
    """
    direction = np.sign(close.diff()).fillna(0)
    obv = (direction * volume).cumsum()
    return obv


def compute_obv_trend(close: pd.Series, volume: pd.Series, period: int = 5) -> pd.Series:
    """
    OBV trend — slope of OBV over `period` bars.
    Positive = accumulation, Negative = distribution.
    Returns normalized slope.
    """
    obv = compute_obv(close, volume)
    obv_sma = compute_sma(obv, period)
    obv_sma_prev = obv_sma.shift(period)
    # Normalize by mean volume to make comparable across symbols
    mean_vol = volume.rolling(window=period, min_periods=1).mean().replace(0, np.nan)
    trend = (obv_sma - obv_sma_prev) / (mean_vol * period)
    return trend


# ──────────────────────────────────────────────
#  VWAP (Volume Weighted Average Price)
# ──────────────────────────────────────────────

def compute_vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> pd.Series:
    """
    Volume Weighted Average Price (intraday — assumes data within one session).
    """
    typical_price = (high + low + close) / 3.0
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum().replace(0, np.nan)
    return cumulative_tp_vol / cumulative_vol


# ──────────────────────────────────────────────
#  Volume Analysis
# ──────────────────────────────────────────────

def compute_volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    """Current volume / N-day average volume."""
    avg_vol = compute_sma(volume, period)
    return volume / avg_vol.replace(0, np.nan)


def compute_volume_trend(volume: pd.Series, period: int = 5) -> pd.Series:
    """Linear slope of volume over `period` bars, normalized."""
    mean_vol = volume.rolling(window=period, min_periods=period).mean().replace(0, np.nan)
    slopes = volume.rolling(window=period, min_periods=period).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == period else 0,
        raw=True,
    )
    return slopes / mean_vol


# ──────────────────────────────────────────────
#  RSI Divergence
# ──────────────────────────────────────────────

def compute_rsi_divergence(close: pd.Series, period: int = 14, lookback: int = 10) -> pd.Series:
    """
    Detect RSI divergence vs price.
    +1 = bullish divergence (price lower low, RSI higher low)
    -1 = bearish divergence (price higher high, RSI lower high)
     0 = no divergence
    """
    rsi = compute_rsi(close, period)
    result = pd.Series(0, index=close.index)

    price_change = close.diff(lookback)
    rsi_change = rsi.diff(lookback)

    # Bullish: price falling but RSI rising
    bullish = (price_change < 0) & (rsi_change > 0)
    # Bearish: price rising but RSI falling
    bearish = (price_change > 0) & (rsi_change < 0)

    result[bullish] = 1
    result[bearish] = -1
    return result


# ──────────────────────────────────────────────
#  MACD Crossover Signal
# ──────────────────────────────────────────────

def compute_macd_crossover(series: pd.Series) -> pd.Series:
    """
    MACD crossover signal.
    +1 = bullish crossover (MACD crosses above signal)
    -1 = bearish crossover (MACD crosses below signal)
     0 = no crossover
    """
    macd_df = compute_macd(series)
    macd_line = macd_df["macd"]
    signal_line = macd_df["signal"]

    prev_diff = (macd_line - signal_line).shift(1)
    curr_diff = macd_line - signal_line

    result = pd.Series(0, index=series.index)
    result[(prev_diff <= 0) & (curr_diff > 0)] = 1   # bullish cross
    result[(prev_diff >= 0) & (curr_diff < 0)] = -1  # bearish cross
    return result
