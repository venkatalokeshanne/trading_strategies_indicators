/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : TU RSI Crossover Signals
 * Author       : tungmeister
 * Source URL   : https://www.tradingview.com/script/qNowfmoK-TU-RSI-Crossover-Signals
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : TU RSI Crossover Signals_TV
 *
 * The Pine original, in words: buy when RSI(14) crosses above its SMA(14) while RSI < 45 (optionally close > EMA
 *   9); sell when it crosses below while RSI > 65.
 *
 * Deviations from the original: input titles shortened (TrendSpider limit).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('TU RSI Crossover Signals_TV', 'price');

// --- Input Settings ---
const myRsiLength = input.number('RSI Length', 14, { min: 1 });
const myMaLength = input.number('RSI MA Length', 14, { min: 1 });
const mySourceName = input.select('Source', 'close', constants.price_source_options);
const mySource = market[mySourceName];

// --- RSI Filter Settings ---
const myBuyFilter = input.number('Max RSI for Buy', 45, { min: 0, max: 100 });
const mySellFilter = input.number('Min RSI for Sell', 65, { min: 0, max: 100 });

// --- Momentum Filter Settings ---
const myUseTrendFilter = input.boolean('Require Price > EMA', false);
const myEmaLength = input.number('Trend EMA Length', 9, { min: 1 });

// --- Calculations ---
const myRsiVal = rsi(mySource, myRsiLength);
const myRsiMa = sma(myRsiVal, myMaLength);
const myEmaVal = ema(mySource, myEmaLength);

// --- Crossover Conditions (replicating ta.crossover / ta.crossunder) ---
const myPrevRsiVal = shift(myRsiVal, 1);
const myPrevRsiMa = shift(myRsiMa, 1);

const myBuyCross = for_every(myRsiVal, myRsiMa, myPrevRsiVal, myPrevRsiMa,
	(_rsi, _ma, _prsi, _pma) => _pma !== null && _rsi > _ma && _prsi <= _pma);

const mySellCross = for_every(myRsiVal, myRsiMa, myPrevRsiVal, myPrevRsiMa,
	(_rsi, _ma, _prsi, _pma) => _pma !== null && _rsi < _ma && _prsi >= _pma);

// --- Momentum Logic ---
const myTrendIsUp = for_every(close, myEmaVal,
	(_close, _ema) => myUseTrendFilter ? (_close > _ema) : true);

const myBuySignal = for_every(myBuyCross, myRsiVal, myTrendIsUp,
	(_cross, _rsi, _trendUp) => _cross && (_rsi < myBuyFilter) && _trendUp);

const mySellSignal = for_every(mySellCross, myRsiVal,
	(_cross, _rsi) => _cross && (_rsi > mySellFilter));

// --- Plot Signals on Price Chart ---
const myBuyMarks = for_every(myBuySignal, _buy => _buy ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellSignal, _sell => _sell ? constants.icons.triangle_down : null);

paint(myBuyMarks, { style: 'labels_below', color: 'green', name: 'Buy Signal' });
paint(mySellMarks, { style: 'labels_above', color: 'red', name: 'Sell Signal' });

// --- Plot the Trend EMA (only when the trend filter is enabled) ---
const myEmaToPlot = myUseTrendFilter ? myEmaVal : series_of(null);
paint(myEmaToPlot, { name: 'Trend EMA', color: 'rgba(0,0,255,0.4)', thickness: 2 });

// --- Signals for scanners/alerts/strategies ---
// Each signal is registered exactly once, with a unique name,
// outside of any conditional block, as required by the engine.
register_signal(myBuySignal, 'Buy Signal Register');
register_signal(mySellSignal, 'Sell Signal Register');
