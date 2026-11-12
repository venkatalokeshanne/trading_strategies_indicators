/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Jewel Lite - Momentum Warning Panel
 * Author       : ketonk
 * Source URL   : https://www.tradingview.com/script/kFawjrGr-Jewel-Lite-Momentum-Warning-Panel
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Jewel Lite - Momentum Warning Panel_TV
 *
 * The Pine original, in words: stochastic of RSI(10) over 14 bars, %K = SMA 3, %D = SMA 3 of %K; levels 80/50/20.
 *
 * Deviations from the original: cross and zone signals added for scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Jewel Lite - Momentum Warning Panel_TV', 'lower');

// Inputs mirroring the original Pine Script inputs
const myRsiLength = input.number('RSI Length', 10, { min: 1, max: 200 });
const myStochLength = input.number('Stochastic Length', 14, { min: 1, max: 200 });
const myKSmooth = input.number('K Smoothing', 3, { min: 1, max: 200 });
const myDSmooth = input.number('D Smoothing', 3, { min: 1, max: 200 });

// Step 1: RSI of close
const myRsiValue = rsi(close, myRsiLength);

// Step 2: Lowest/Highest of RSI over stoch length
const myLowRsi = lowest(myRsiValue, myStochLength);
const myHighRsi = highest(myRsiValue, myStochLength);

// Step 3: Raw Stochastic RSI, defaulting to 50 when range is 0
// (exact translation of the Pine ternary expression)
const myRawStoch = for_every(myRsiValue, myLowRsi, myHighRsi, (_rsi, _lo, _hi) => {
	const myRange = _hi - _lo;
	return myRange > 0 ? ((_rsi - _lo) / myRange) * 100 : 50;
});

// Step 4: Smooth outputs
const myLineK = sma(myRawStoch, myKSmooth);
const myLineD = sma(myLineK, myDSmooth);

// Reference structure levels
paint(horizontal_line(80), { name: 'Overbought', color: 'red', style: 'dotted' });
paint(horizontal_line(50), { name: 'Median', color: 'gray', style: 'dotted' });
paint(horizontal_line(20), { name: 'Oversold', color: 'green', style: 'dotted' });

// Main lines
paint(myLineK, { name: 'Jewel Fast Momentum (%K)', color: '#00e5ff', thickness: 2 });
paint(myLineD, { name: 'Jewel Slow Signal (%D)', color: '#2962ff', thickness: 2 });

// Scanner/strategy signals
const myCrossUp = for_every(myLineK, myLineD, (_k, _d, _prev, _idx) => {
	if (_idx === 0) return false;
	return _d !== null && myLineD[_idx - 1] !== null && _k > _d && myLineK[_idx - 1] <= myLineD[_idx - 1];
});

const myCrossDown = for_every(myLineK, myLineD, (_k, _d, _prev, _idx) => {
	if (_idx === 0) return false;
	return _d !== null && myLineD[_idx - 1] !== null && _k < _d && myLineK[_idx - 1] >= myLineD[_idx - 1];
});

const myOverbought = for_every(myLineK, _k => _k !== null && _k > 80);
const myOversold = for_every(myLineK, _k => _k !== null && _k < 20);

register_signal(myCrossUp, 'K Crosses Above D');
register_signal(myCrossDown, 'K Crosses Below D');
register_signal(myOverbought, 'Overbought (K above 80)');
register_signal(myOversold, 'Oversold (K below 20)');
