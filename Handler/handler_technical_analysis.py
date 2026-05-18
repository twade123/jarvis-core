"""
Technical Analysis MCP Handler — Exposes TA modules as sync tools for the LLM agent.

Same pattern as DataValidatorHandler: sync wrapper methods that the SwarmHandler
introspects into Anthropic tool definitions. The technical_analyst LLM agent
decides which tools to call based on candle data and market conditions.

Tools:
    compute_core_indicators  — EMA, RSI, MACD, Bollinger Bands, ATR
    compute_advanced_indicators — ADX, Stochastic, Volume SMA, Fibonacci, VWAP
    detect_candlestick_patterns — 61 TA-Lib CDL* patterns with priority/direction
    detect_chart_patterns — H&S, double top/bottom, triangles, flags, etc.
    check_multi_timeframe_alignment — H4/H1/M15 directional alignment + weighted score
    compute_confluence_score — Combine indicator results into 0-100 score
    detect_regime — Trending/ranging/volatile classification from ADX
    scan_setups — Fire specific trade setups from backtester pattern library
    get_h4_trend — Higher timeframe bias from H4 candles
    detect_session — Current trading session (London/NY/Asian/Off-Hours)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("handler.technical_analysis")

# ---------------------------------------------------------------------------
# Lazy imports — avoid heavy loads at module level
# ---------------------------------------------------------------------------

def _get_indicators():
    from Source.indicators import Indicators
    return Indicators

def _get_advanced_indicators():
    from Source.indicators_advanced import AdvancedIndicators
    return AdvancedIndicators

def _get_candlestick_patterns():
    from Source.candlestick_patterns import CandlestickPatterns
    return CandlestickPatterns

def _get_chart_patterns():
    from Source.chart_patterns import ChartPatterns
    return ChartPatterns

def _get_confluence_scorer():
    from Source.confluence_scorer import ConfluenceScorer
    return ConfluenceScorer

def _get_alignment():
    from Source.alignment import MultiTimeframeAlignment
    return MultiTimeframeAlignment


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable types."""
    import numpy as np
    import pandas as pd
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (pd.Timestamp,)):
        return str(obj)
    elif isinstance(obj, (pd.Series,)):
        return obj.tolist()
    elif isinstance(obj, float) and (obj != obj):  # NaN
        return None
    return obj


class TechnicalAnalysisMCPHandler:
    """Sync tool wrappers for the technical_analyst LLM agent.
    
    The agent receives candle data in its task prompt and uses these tools
    to run specific analyses. It decides what to run based on market conditions
    rather than blindly running everything.
    
    Candle data is pre-loaded via load_candles() before the LLM agent runs.
    Tools reference stored candles by timeframe key (e.g. "H1", "H4", "M15")
    so the LLM doesn't need to pass giant JSON arrays.
    """

    def __init__(self):
        # Candle data loaded before agent runs — keyed by timeframe
        self._candles: Dict[str, List[Dict]] = {}
        self._instrument: str = ""
        self._news_score: float = 0.0

    def load_candles(self, candles_by_tf: Dict[str, List[Dict]], 
                     instrument: str = "", news_score: float = 0.0):
        """Pre-load candle data before LLM agent execution.
        Called by trading_cycle.py before _agent_task().
        """
        self._candles = candles_by_tf or {}
        self._instrument = instrument
        self._news_score = news_score
        logger.info("TA handler loaded candles: %s", 
                     {tf: len(c) for tf, c in self._candles.items()})

    def _get_candles(self, timeframe: str = "H1") -> List[Dict]:
        """Get pre-loaded candles for a timeframe."""
        candles = self._candles.get(timeframe)
        if candles:
            return candles
        # Fall back to first available
        if self._candles:
            return next(iter(self._candles.values()))
        return []

    def get_candle_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded candle data: timeframes available, candle counts, and recent price action (last 5 candles per timeframe).
        
        Call this FIRST to understand what data you have before running analysis tools.
        No arguments needed.
        
        Returns:
            Dict with instrument, timeframes, candle counts, and last 5 candles per timeframe
        """
        summary = {
            "instrument": self._instrument,
            "timeframes_available": list(self._candles.keys()),
            "candle_counts": {tf: len(c) for tf, c in self._candles.items()},
            "news_score": self._news_score,
        }
        # Include last 5 candles per timeframe for the LLM to see recent price action
        for tf, candles in self._candles.items():
            if candles:
                last_5 = candles[-5:]
                summary[f"recent_{tf}"] = [
                    {
                        "time": c.get("time", ""),
                        "open": c.get("open"),
                        "high": c.get("high"),
                        "low": c.get("low"),
                        "close": c.get("close"),
                        "volume": c.get("volume"),
                    }
                    for c in last_5
                ]
        return _sanitize_for_json(summary)

    def compute_core_indicators(self, timeframe: str = "H1") -> Dict[str, Any]:
        """Compute core technical indicators: EMA(21/55/100), RSI(14), MACD(12,26,9), Bollinger Bands(20,2), ATR(14).
        
        Args:
            timeframe: Which timeframe to analyze (H1, H4, M15). Default H1.
            
        Returns:
            Dict with emas, ema_crossovers, rsi, rsi_divergence, macd, bollinger, atr
        """
        try:
            candles = self._get_candles(timeframe)
            if not candles or len(candles) < 20:
                return {"error": f"Need at least 20 candles for {timeframe}, got {len(candles)}"}
            IndicatorsClass = _get_indicators()
            calc = IndicatorsClass(candles)
            result = calc.compute_all()
            return _sanitize_for_json(result)
        except Exception as e:
            logger.error("compute_core_indicators failed: %s", e)
            return {"error": str(e)}

    def compute_advanced_indicators(self, timeframe: str = "H1") -> Dict[str, Any]:
        """Compute advanced indicators: ADX (trend strength), Stochastic (momentum extremes), Volume SMA, Fibonacci levels, VWAP.
        
        ADX > 25 = trending market, ADX < 20 = ranging market.
        Stochastic > 80 = overbought, < 20 = oversold.
        
        Args:
            timeframe: Which timeframe to analyze (H1, H4, M15). Default H1.
            
        Returns:
            Dict with adx, stochastic, volume_sma, fibonacci, vwap
        """
        try:
            candles = self._get_candles(timeframe)
            if not candles or len(candles) < 20:
                return {"error": f"Need at least 20 candles for {timeframe}, got {len(candles)}"}
            AdvClass = _get_advanced_indicators()
            calc = AdvClass(candles)
            result = calc.compute_all()
            return _sanitize_for_json(result)
        except Exception as e:
            logger.error("compute_advanced_indicators failed: %s", e)
            return {"error": str(e)}

    def detect_candlestick_patterns(self, timeframe: str = "H1") -> Dict[str, Any]:
        """Detect candlestick patterns using TA-Lib (61 patterns). Returns detected patterns with priority (HIGH/MEDIUM/LOW) and direction (bullish/bearish).
        
        Key patterns: hammer, engulfing, morning/evening star, doji, harami, piercing line, dark cloud cover.
        
        Args:
            timeframe: Which timeframe to scan (H1, H4, M15). Default H1.
            
        Returns:
            Dict with detected_count, filtered_patterns (list of {pattern, name, direction, strength, priority})
        """
        try:
            candles = self._get_candles(timeframe)
            if not candles or len(candles) < 5:
                return {"error": f"Need at least 5 candles for {timeframe}, got {len(candles)}"}
            CSClass = _get_candlestick_patterns()
            detector = CSClass(candles)
            result = detector.get_detected_patterns()
            return _sanitize_for_json(result)
        except Exception as e:
            logger.error("detect_candlestick_patterns failed: %s", e)
            return {"error": str(e)}

    def detect_chart_patterns(self, timeframe: str = "H1") -> Dict[str, Any]:
        """Detect chart patterns: head & shoulders, double top/bottom, triangles, flags, wedges, cup & handle.
        
        Each pattern includes: type, direction, confirmed (bool), target price, stop level, confidence.
        
        Args:
            timeframe: Which timeframe to scan (H1, H4, M15). Default H1.
            
        Returns:
            Dict with patterns list, reversal_patterns, continuation_patterns
        """
        try:
            candles = self._get_candles(timeframe)
            if not candles or len(candles) < 30:
                return {"error": f"Need at least 30 candles for chart patterns on {timeframe}, got {len(candles)}"}
            CPClass = _get_chart_patterns()
            detector = CPClass(candles)
            result = detector.scan_all()
            return _sanitize_for_json(result)
        except Exception as e:
            logger.error("detect_chart_patterns failed: %s", e)
            return {"error": str(e)}

    def check_multi_timeframe_alignment(self) -> Dict[str, Any]:
        """Check alignment across all loaded timeframes (H4, H1, M15). Returns weighted directional score (H4=0.45, H1=0.35, M15=0.20) and alignment classification.
        
        Bullish aligned = all timeframes agree bullish → strong signal.
        Mixed = timeframes disagree → weak signal, avoid trading.
        
        No arguments needed — uses pre-loaded candle data for all timeframes.
            
        Returns:
            Dict with alignment classification, directional_score, per-timeframe signals
        """
        try:
            if not self._candles:
                return {"error": "No candle data loaded"}
            AlignClass = _get_alignment()
            checker = AlignClass(self._candles)
            result = checker.get_snapshot()
            return _sanitize_for_json(result)
        except Exception as e:
            logger.error("check_multi_timeframe_alignment failed: %s", e)
            return {"error": str(e)}

    def compute_confluence_score(self, 
                                 core_indicators_json: str = "{}",
                                 advanced_indicators_json: str = "{}",
                                 alignment_snapshot_json: str = "{}",
                                 candlestick_patterns_json: str = "{}",
                                 chart_patterns_json: str = "{}",
                                 news_score: float = 0.0) -> Dict[str, Any]:
        """Compute the 0-100 confluence score from indicator results. This combines all signal sources with regime-adjusted weights.
        
        Score >= 70 = tradeable signal. Score < 50 = no trade. 50-70 = weak, needs extra confirmation.
        
        Uses ADX to detect regime (trending/ranging) and adjusts weights:
        - Trending: EMA and MACD boosted, Bollinger and Stochastic reduced
        - Ranging: Bollinger and Stochastic boosted, EMA and MACD reduced
        
        Args:
            core_indicators_json: JSON output from compute_core_indicators
            advanced_indicators_json: JSON output from compute_advanced_indicators
            alignment_snapshot_json: JSON output from check_multi_timeframe_alignment
            candlestick_patterns_json: JSON output from detect_candlestick_patterns
            chart_patterns_json: JSON output from detect_chart_patterns
            news_score: Float 0-5, sentiment magnitude from intelligence agent
            
        Returns:
            Dict with total_score, regime, direction, breakdown (per-source scores), threshold
        """
        try:
            def _load(v):
                if isinstance(v, dict):
                    return v
                try:
                    return json.loads(v) if v else {}
                except (json.JSONDecodeError, TypeError):
                    return {}

            core = _load(core_indicators_json)
            advanced = _load(advanced_indicators_json)
            alignment = _load(alignment_snapshot_json)
            cs_patterns = _load(candlestick_patterns_json)
            ch_patterns = _load(chart_patterns_json)

            ScorerClass = _get_confluence_scorer()
            scorer = ScorerClass()
            result = scorer.compute_score(
                indicators_result=core,
                advanced_result=advanced,
                alignment_snapshot=alignment,
                pattern_results=cs_patterns,
                chart_results=ch_patterns,
                news_data={"score": news_score} if news_score else None,
            )
            return _sanitize_for_json(result)
        except Exception as e:
            logger.error("compute_confluence_score failed: %s", e)
            return {"error": str(e)}

    def detect_regime(self, timeframe: str = "H1") -> Dict[str, Any]:
        """Detect market regime from candle data: trending, ranging, or volatile.
        
        Uses ADX value + price action analysis.
        - Trending (ADX > 25): follow the trend, use EMA/MACD signals
        - Ranging (ADX < 20): mean reversion, use RSI/Stochastic/BB extremes
        - Volatile: wider stops needed, reduce position size
        
        Args:
            timeframe: Which timeframe to check regime on (H1, H4). Default H1.
            
        Returns:
            Dict with regime, adx_value, description
        """
        try:
            candles = self._get_candles(timeframe)
            if not candles or len(candles) < 20:
                return {"regime": "unknown", "error": f"Need 20+ candles for {timeframe}, got {len(candles)}"}
            
            AdvClass = _get_advanced_indicators()
            calc = AdvClass(candles)
            result = calc.compute_all()
            adx_data = result.get("adx", {})
            adx_val = adx_data.get("value", adx_data.get("adx", 0))
            
            if adx_val >= 25:
                regime = "trending"
                desc = f"ADX={adx_val:.1f} — strong trend. Favor EMA/MACD trend-following signals."
            elif adx_val <= 20:
                regime = "ranging"
                desc = f"ADX={adx_val:.1f} — range-bound. Favor RSI/Stochastic/Bollinger mean-reversion signals."
            else:
                regime = "mixed"
                desc = f"ADX={adx_val:.1f} — transitional. Both trend and mean-reversion signals may work."
            
            return _sanitize_for_json({
                "regime": regime,
                "adx_value": adx_val,
                "adx_trend": adx_data.get("trend", "unknown"),
                "description": desc,
            })
        except Exception as e:
            return {"regime": "unknown", "error": str(e)}

    def detect_session(self) -> Dict[str, Any]:
        """Detect current forex trading session based on UTC time.
        
        Returns:
            Dict with session name, description, and trading recommendation
        """
        try:
            from Source.agents.wrappers import detect_session as _detect_session
            session = _detect_session()
            
            session_info = {
                "London": "London session (03:00-12:00 ET) — highest EUR/GBP volatility, best for European pairs.",
                "New_York": "New York session (08:00-17:00 ET) — highest USD volatility, best overlap with London 08:00-12:00.",
                "London_NY_Overlap": "London-NY overlap (08:00-12:00 ET) — PEAK volatility, best trading window.",
                "Asian": "Asian session (19:00-04:00 ET) — lower volatility, JPY/AUD pairs most active.",
                "Off_Hours": "Off-hours — low liquidity, wider spreads. Avoid new entries unless strong signal.",
            }
            
            return {
                "session": session,
                "description": session_info.get(session, "Unknown session"),
                "peak_trading": session in ("London_NY_Overlap", "London", "New_York"),
            }
        except Exception as e:
            return {"session": "unknown", "error": str(e)}

    def get_h4_trend(self) -> Dict[str, Any]:
        """Determine higher timeframe (H4) trend bias using EMA stack and price position.
        
        H4 trend alignment with H1 signals adds +4.1 percentage points to win rate (backtest-proven).
        Uses pre-loaded H4 candles. No arguments needed.
            
        Returns:
            Dict with trend direction, EMA positions, confidence
        """
        try:
            candles = self._candles.get("H4", [])
            if not candles or len(candles) < 20:
                return {"trend": "unknown", "error": f"Need 20+ H4 candles, got {len(candles)}"}
            
            IndicatorsClass = _get_indicators()
            calc = IndicatorsClass(candles)
            result = calc.compute_all()
            
            emas = result.get("emas", {})
            ema_21 = emas.get("21", [])
            ema_55 = emas.get("55", [])
            ema_100 = emas.get("100", [])
            
            trend = "unknown"
            if ema_21 and ema_55 and ema_100:
                last_21 = ema_21[-1] if ema_21 else 0
                last_55 = ema_55[-1] if ema_55 else 0
                last_100 = ema_100[-1] if ema_100 else 0
                
                if last_21 > last_55 > last_100:
                    trend = "bullish"
                elif last_21 < last_55 < last_100:
                    trend = "bearish"
                else:
                    trend = "neutral"
            
            rsi = result.get("rsi", {})
            
            return _sanitize_for_json({
                "trend": trend,
                "ema_21": ema_21[-1] if ema_21 else None,
                "ema_55": ema_55[-1] if ema_55 else None,
                "ema_100": ema_100[-1] if ema_100 else None,
                "rsi": rsi.get("value"),
                "rsi_overbought": rsi.get("overbought", False),
                "rsi_oversold": rsi.get("oversold", False),
            })
        except Exception as e:
            return {"trend": "unknown", "error": str(e)}


# Singleton for handler registry
_handler_instance = None

def get_handler() -> TechnicalAnalysisMCPHandler:
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = TechnicalAnalysisMCPHandler()
    return _handler_instance
