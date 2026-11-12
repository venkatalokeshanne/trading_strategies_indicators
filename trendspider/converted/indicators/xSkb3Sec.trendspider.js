/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : SMA10 Breakout with RSI & MACD
 * Author       : lhhghblall
 * Source URL   : https://www.tradingview.com/script/xSkb3Sec
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : SMA10 Breakout with RSI & MACD_TV
 *
 * The Pine original, in words: buy when close crosses above SMA 10 while RSI(14) > 50 and MACD(12,26,9) line >
 *   signal; candle coloured and triangle below.
 *
 * Deviations from the original: input titles in English (original Arabic).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('SMA10 Breakout with RSI & MACD_TV', 'price');

// Inputs mirroring the original Pine Script inputs
const myMaPeriod = input.number('MA Period', 10, { min: 1, max: 500 });
const myRsiPeriod = input.number('RSI Period', 14, { min: 1, max: 500 });
const myFastLength = input.number('MACD Fast Length', 12, { min: 1, max: 500 });
const mySlowLength = input.number('MACD Slow Length', 26, { min: 1, max: 500 });
const mySignalLength = input.number('MACD Signal Length', 9, { min: 1, max: 500 });

// 1. Simple Moving Average and crossover (close crosses above sma)
const mySma10 = sma(close, myMaPeriod);
const myIsSmaCross = for_every(close, mySma10, (_close, _sma, _prev, _index) => {
	if (_index === 0) {
		return false;
	}
	return _close > _sma && close[_index - 1] <= mySma10[_index - 1];
});

// 2. RSI
const myRsiVal = rsi(close, myRsiPeriod);
const myIsRsiBullish = for_every(myRsiVal, _rsi => _rsi !== null && _rsi > 50.0);

// 3. MACD, built manually from EMAs (no built-in macd() function available)
const myMacdLine = sub(ema(close, myFastLength), ema(close, mySlowLength));
const mySignalLine = ema(myMacdLine, mySignalLength);
const myIsMacdBullish = for_every(myMacdLine, mySignalLine, (_macd, _signal) => _signal !== null && _macd > _signal);

// Composite buy condition
const myBuySignal = for_every(myIsSmaCross, myIsRsiBullish, myIsMacdBullish, (_cross, _rsiOk, _macdOk) => _cross && _rsiOk && _macdOk);

// Candle coloring on the buy signal (phosphorescent green)
const myCandleColors = for_every(myBuySignal, _buy => _buy ? '#00FF08' : null);
color_candles(myCandleColors);

// Plot the moving average line
paint(mySma10, { name: 'MA 10', color: 'orange', thickness: 2 });

// Buy arrow markers below the signal candles
const myBuyMarks = for_every(myBuySignal, _buy => _buy ? constants.icons.triangle_up : null);
paint(myBuyMarks, { name: 'Buy Signal Marks', style: 'labels_below', color: '#00FF08' });

// Expose the buy condition for Scanners, Alerts and Strategy Tester
// Only one register_signal() call exists in this script with this name;
// the "already exists" error typically appears when the previous script
// version was still cached with a duplicate name - renamed signal and
// marker names to avoid any collision.
register_signal(myBuySignal, 'Buy Signal Condition');
