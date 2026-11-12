/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : SMA 333
 * Author       : sanremopalmer1
 * Source URL   : https://www.tradingview.com/script/z880j8UQ-SMA-333
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : SMA 333_TV
 *
 * The Pine original, in words: SMA(9) of a source, with optional smoothing MA (SMA/EMA/RMA/WMA/VWMA) and Bollinger
 *   Bands around it.
 *
 * Deviations from the original: plot offset input not carried over; price/SMA signals added for scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('SMA 333_TV', 'price');

// Inputs matching Pine script
const myLen = input.number('Length', 9, { min: 1, max: 500 });
const myPriceSource = input.select('Source', 'close', constants.price_source_options);
const mySrc = market[myPriceSource];

const smoothingTab = input.tab('Smoothing');
const myMaType = smoothingTab.select('Type', 'None', ['None', 'SMA', 'SMA + Bollinger Bands', 'EMA', 'SMMA (RMA)', 'WMA', 'VWMA']);
const myMaLength = smoothingTab.number('Length', 14, { min: 1, max: 500 });
const myBbMult = smoothingTab.number('BB StdDev', 2.0, { min: 0.001, max: 50, step: 0.5 });

// Main SMA line
const myOut = sma(mySrc, myLen);
paint(myOut, { name: 'MA', color: 'blue' });

const myEnableMA = myMaType !== 'None';
const myIsBB = myMaType === 'SMA + Bollinger Bands';

// Computes the chosen smoothing MA type over the main SMA line
function myComputeSmoothingMA(_source, _length, _type) {
	if (_type === 'SMA' || _type === 'SMA + Bollinger Bands') {
		return sma(_source, _length);
	}
	else if (_type === 'EMA') {
		return ema(_source, _length);
	}
	else if (_type === 'SMMA (RMA)') {
		return wildma(_source, _length);
	}
	else if (_type === 'WMA') {
		return wma(_source, _length);
	}
	else if (_type === 'VWMA') {
		return vwma(_source, _length);
	}
	return series_of(null);
}

const mySmoothingMA = myEnableMA ? myComputeSmoothingMA(myOut, myMaLength, myMaType) : series_of(null);
const mySmoothingStDev = myIsBB ? mult(stdev(myOut, myMaLength), myBbMult) : series_of(null);

const myUpperBand = myIsBB ? add(mySmoothingMA, mySmoothingStDev) : series_of(null);
const myLowerBand = myIsBB ? sub(mySmoothingMA, mySmoothingStDev) : series_of(null);

const mySmoothingLinePainted = paint(myEnableMA ? mySmoothingMA : series_of(null), { name: 'SMA-based MA', color: 'yellow' });
const myUpperBandPainted = paint(myIsBB ? myUpperBand : series_of(null), { name: 'Upper Bollinger Band', color: 'green' });
const myLowerBandPainted = paint(myIsBB ? myLowerBand : series_of(null), { name: 'Lower Bollinger Band', color: 'green' });

fill(myUpperBandPainted, myLowerBandPainted, 'green', 0.1);

// Signals for scanners/alerts/strategies: price crossing the main SMA
const myCrossAbove = for_every(mySrc, myOut, (_s, _m, _prev, _i) => {
	return _i > 0 && _m !== null && myOut[_i - 1] !== null && _s > _m && mySrc[_i - 1] <= myOut[_i - 1];
});
const myCrossBelow = for_every(mySrc, myOut, (_s, _m, _prev, _i) => {
	return _i > 0 && _m !== null && myOut[_i - 1] !== null && _s < _m && mySrc[_i - 1] >= myOut[_i - 1];
});

register_signal(myCrossAbove, 'Price Crossed Above SMA');
register_signal(myCrossBelow, 'Price Crossed Below SMA');
register_signal(for_every(mySrc, myOut, (_s, _m) => _m !== null && _s > _m), 'Price Above SMA');
register_signal(for_every(mySrc, myOut, (_s, _m) => _m !== null && _s < _m), 'Price Below SMA');
