describe_indicator('BTC Long Short Trend System', 'price');

// NOTE: TrendSpider Custom JS has no native strategy engine (no
// strategy.entry/exit, no trailing stop simulation). This script
// reproduces the Pine SIGNAL LOGIC (EMA200 + SuperTrend flip) as
// an indicator with register_signal() outputs for Long/Short entry
// and trend reversal exit, so it can be used in Scanners/Alerts.
// The percent-based trailing stop exit from the Pine script cannot
// be expressed here and is NOT reproduced.

const myTab = input.tab('Settings');
const myEmaLength = myTab.number('EMA Length (trend filter)', 200, { min: 1, max: 1000 });
const myAtrPeriod = myTab.number('SuperTrend ATR Period', 10, { min: 1, max: 200 });
const myFactor = myTab.number('SuperTrend Multiplier', 3, { min: 0.1, max: 20 });

// Core calculations
const myEma200 = ema(close, myEmaLength);
const mySupertrend = supertrend(myAtrPeriod, myFactor, false);

// The built-in supertrend() only returns the line itself, not a
// separate direction series like Pine's ta.supertrend(). We derive
// direction the same way Pine effectively uses it: close above the
// SuperTrend line means uptrend (Pine direction < 0), close below
// means downtrend (Pine direction > 0).
const myDirection = for_every(close, mySupertrend, (_c, _s) => _c > _s ? -1 : 1);
const myPrevDirection = shift(myDirection, 1);

// Entry conditions (flip detection, same as Pine's direction[1] check)
const myLongCondition = for_every(close, myEma200, myDirection, myPrevDirection,
	(_c, _e, _d, _p) => (_c > _e && _d < 0 && _p > 0));

const myShortCondition = for_every(close, myEma200, myDirection, myPrevDirection,
	(_c, _e, _d, _p) => (_c < _e && _d > 0 && _p < 0));

// Reversal-based exit ("base signal reversal close" in Pine)
const myExitLongOnReversal = for_every(myDirection, _d => _d > 0);
const myExitShortOnReversal = for_every(myDirection, _d => _d < 0);

register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myExitLongOnReversal, 'Exit Long Trend Reversal');
register_signal(myExitShortOnReversal, 'Exit Short Trend Reversal');

// Plotting: EMA200 and SuperTrend support/resistance segments
paint(myEma200, { name: 'EMA200', color: 'gray', thickness: 2 });

const myUpSupportLine = for_every(mySupertrend, myDirection, (_s, _d) => _d < 0 ? _s : null);
const myDownResistanceLine = for_every(mySupertrend, myDirection, (_s, _d) => _d > 0 ? _s : null);

paint(myUpSupportLine, { name: 'Up Support Line', color: 'green', style: 'line' });
paint(myDownResistanceLine, { name: 'Down Resistance Line', color: 'red', style: 'line' });

// Background highlight approximation (Pine bgcolor) using candle coloring
const myBackgroundColor = for_every(close, myEma200, myDirection, (_c, _e, _d) => {
	if (_d < 0 && _c > _e) {
		return 'rgba(0,200,83,0.12)';
	}
	if (_d > 0 && _c < _e) {
		return 'rgba(255,23,68,0.12)';
	}
	return null;
});

color_candles(myBackgroundColor);