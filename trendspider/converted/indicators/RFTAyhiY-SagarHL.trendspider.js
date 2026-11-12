/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Sagar Volume
 * Author       : sagarjena02
 * Source URL   : https://www.tradingview.com/script/RFTAyhiY-SagarHL
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Sagar Volume_TV
 *
 * The Pine original, in words: volume of the continuous futures contract (<ticker>1!) as columns, with EMA 20 and
 *   EMA 50 of it.
 *
 * Deviations from the original: uses the chart's own volume: TrendSpider cannot address TradingView's '<ticker>1!'
 *   continuous-futures symbols — open the indicator on the futures chart.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Sagar Volume_TV', 'lower');

// Inputs for the two volume EMA lengths
const myMa1Length = input.number('Volume MA 1', 20, { min: 1, max: 500 });
const myMa2Length = input.number('Volume MA 2', 50, { min: 1, max: 500 });

// NOTE: TrendSpider's Custom JS API has no equivalent of Pine's
// syminfo.prefix / request.security() that lets us build an arbitrary
// continuous futures ticker string (e.g. "BINANCE:BTCUSD1!") on the fly.
// As a workaround we use the current chart's own volume series as a
// proxy for "futuresVolume". If the chart's symbol already IS the
// futures contract, this is exact; otherwise it is an approximation.
// TrendSpider: uses the chart's own volume — open this on the futures chart (Pine read <prefix>:<ticker>1!).
const myFuturesVolume = volume;

const myVolMA1 = ema(myFuturesVolume, myMa1Length);
const myVolMA2 = ema(myFuturesVolume, myMa2Length);

paint(myFuturesVolume, { name: 'Futures Volume', style: 'column', color: '#2b2b2b' });
paint(myVolMA1, { name: 'Volume EMA 20', color: '#ffffff', thickness: 1 });
paint(myVolMA2, { name: 'Volume EMA 50', color: '#ffffff', thickness: 2 });

// Scanning / strategy signals: volume crossing above/below its EMAs
const myCrossAboveMa1 = for_every(myFuturesVolume, myVolMA1, (_v, _ma, _prev, _i) => {
	if (_i === 0) return false;
	return myFuturesVolume[_i - 1] <= myVolMA1[_i - 1] && _v > _ma;
});

const myCrossBelowMa1 = for_every(myFuturesVolume, myVolMA1, (_v, _ma, _prev, _i) => {
	if (_i === 0) return false;
	return myFuturesVolume[_i - 1] >= myVolMA1[_i - 1] && _v < _ma;
});

const myCrossAboveMa2 = for_every(myFuturesVolume, myVolMA2, (_v, _ma, _prev, _i) => {
	if (_i === 0) return false;
	return myFuturesVolume[_i - 1] <= myVolMA2[_i - 1] && _v > _ma;
});

const myCrossBelowMa2 = for_every(myFuturesVolume, myVolMA2, (_v, _ma, _prev, _i) => {
	if (_i === 0) return false;
	return myFuturesVolume[_i - 1] >= myVolMA2[_i - 1] && _v < _ma;
});

register_signal(myCrossAboveMa1, 'Volume Crossed Above EMA 20');
register_signal(myCrossBelowMa1, 'Volume Crossed Below EMA 20');
register_signal(myCrossAboveMa2, 'Volume Crossed Above EMA 50');
register_signal(myCrossBelowMa2, 'Volume Crossed Below EMA 50');
