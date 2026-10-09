// NOTE: This is a conversion of a TradingView Pine Script v6 strategy into a
// TrendSpider Custom JS indicator. TrendSpider indicators cannot execute real
// broker-style orders (strategy.entry/strategy.exit), so this script
// reproduces the exact same bar-by-bar signal logic (condLong/condShort,
// position-state gating, TP/SL price levels) and exposes them as painted
// shapes, lines and register_signal() outputs usable in scanners/alerts.
// "bgcolor()" (panel background shading) has no direct equivalent in the
// Custom JS API, so the "Narrow State" condition is instead shown as a
// dotted reference line on the price axis.
describe_indicator('Yuri Garcia Narrow State Strategy', 'price');

const mainTab = input.tab('Main');

const atrGroup = mainTab.group('Risk');
const myAtrLen = atrGroup.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMult = atrGroup.number('Stop Mult xATR', 2.0, { min: 0.01, max: 50 });
const myRrr = atrGroup.number('RRR', 2.0, { min: 0.01, max: 50 });
const myTradeDirection = atrGroup.select('Trade Direction', 'Both', ['Both', 'Buy Only', 'Sell Only']);

const trendGroup = mainTab.group('Trend/Pattern');
const myEmaFastLen = trendGroup.number('Fast EMA Length', 20, { min: 1, max: 500 });
const mySmaSlowLen = trendGroup.number('Slow SMA Length', 200, { min: 1, max: 1000 });
const myMultElephant = trendGroup.number('Elephant Bar Multiplier', 1.5, { min: 0.01, max: 50 });
// Shortened title (was too long for the input engine's name length limit)
const myMaxDistancePct = trendGroup.number('Narrow Max Dist Pct', 1.5, { min: 0.001, max: 100 });

const myCanBuy = (myTradeDirection === 'Both' || myTradeDirection === 'Buy Only');
const myCanSell = (myTradeDirection === 'Both' || myTradeDirection === 'Sell Only');

// Pine's syminfo.mintick is approximated via current.decimals (closest
// available proxy in the Custom JS API).
const myTick = Math.pow(10, -current.decimals);

const myAtr = atr(high, low, close, myAtrLen);
const myEma20 = ema(close, myEmaFastLen);
const mySma200 = sma(close, mySmaSlowLen);

const myMaDistancePct = for_every(myEma20, mySma200, (_e, _s) => (_s === null || _s === 0) ? null : Math.abs(_e - _s) / _s * 100);
const myIsNarrowState = for_every(myMaDistancePct, _d => _d !== null && _d <= myMaxDistancePct);

const myBullishTrend = for_every(close, myEma20, mySma200, (_c, _e, _s) => _c > _s && _e > _s);
const myBearishTrend = for_every(close, myEma20, mySma200, (_c, _e, _s) => _c < _s && _e < _s);

const myCandleBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myIsElephant = for_every(myCandleBody, myAtr, (_b, _a) => _a !== null && _b > _a * myMultElephant);

const myBullishElephant = for_every(myIsElephant, close, open, myBullishTrend, (_el, _c, _o, _bt) => _el && _c > _o && _bt);
const myBearishElephant = for_every(myIsElephant, close, open, myBearishTrend, (_el, _c, _o, _bt) => _el && _c < _o && _bt);

const myPrevOpen = shift(open, 1);
const myPrevClose = shift(close, 1);
const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);

const myRbiBuy = for_every(myBullishTrend, myPrevClose, myPrevOpen, close, open, myPrevHigh,
	(_bt, _pc, _po, _c, _o, _ph) => _bt && _pc < _po && _c > _o && _c > _ph);

const myGbiSell = for_every(myBearishTrend, myPrevClose, myPrevOpen, close, open, myPrevLow,
	(_bt, _pc, _po, _c, _o, _pl) => _bt && _pc > _po && _c < _o && _c < _pl);

const myCondLong = for_every(myBullishElephant, myRbiBuy, myIsNarrowState, (_be, _rbi, _ns) => (_be || _rbi) && _ns);
const myCondShort = for_every(myBearishElephant, myGbiSell, myIsNarrowState, (_bere, _gbi, _ns) => (_bere || _gbi) && _ns);

// Position-state gating must be computed sequentially, bar by bar, exactly
// like strategy.position_size behaves in Pine (one position at a time, no
// pyramiding). This is plain JS state tracking, not an indicator call, so a
// regular loop is acceptable here.
const myNewLong = series_of(false);
const myNewShort = series_of(false);
const myLongSL = series_of(null);
const myShortSL = series_of(null);
const myLongTP = series_of(null);
const myShortTP = series_of(null);

let myPositionSize = 0; // >0 long, <0 short, 0 flat

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myLong = myCondLong[myIndex] && myCanBuy && myPositionSize <= 0;
	const myShort = myCondShort[myIndex] && myCanSell && myPositionSize >= 0;

	myNewLong[myIndex] = myLong;
	myNewShort[myIndex] = myShort;

	if (myAtr[myIndex] !== null) {
		myLongSL[myIndex] = Math.round((close[myIndex] - myAtr[myIndex] * myAtrMult) / myTick) * myTick;
		myShortSL[myIndex] = Math.round((close[myIndex] + myAtr[myIndex] * myAtrMult) / myTick) * myTick;
		myLongTP[myIndex] = Math.round((close[myIndex] + myAtr[myIndex] * myAtrMult * myRrr) / myTick) * myTick;
		myShortTP[myIndex] = Math.round((close[myIndex] - myAtr[myIndex] * myAtrMult * myRrr) / myTick) * myTick;
	}

	if (myLong) {
		myPositionSize = 1;
	}
	else if (myShort) {
		myPositionSize = -1;
	}
}

const myEmaColor = for_every(myEma20, mySma200, (_e, _s) => _e > _s ? '#36d957' : '#e3453a');

paint(myEma20, { name: 'EMA20', color: myEmaColor, thickness: 2 });
paint(mySma200, { name: 'SMA200', color: 'white', thickness: 3 });

// Narrow state reference: sparse horizontal line equal to close whenever the
// market is in a "narrow state", used in place of Pine's bgcolor() shading
// (not available in Custom JS API).
const myNarrowStateMarker = for_every(myIsNarrowState, close, (_ns, _c) => _ns ? _c : null);
paint(myNarrowStateMarker, { name: 'NarrowStateLine', style: 'dotted', color: '#2ecc71' });

const myBuyShape = for_every(myNewLong, _b => _b ? constants.icons.triangle_up : null);
const mySellShape = for_every(myNewShort, _s => _s ? constants.icons.triangle_down : null);

paint(myBuyShape, { name: 'Buy', style: 'labels_below', color: '#36d957' });
paint(mySellShape, { name: 'Sell', style: 'labels_above', color: '#e3453a' });

paint(myLongSL, { name: 'Long Stop Loss', style: 'dotted', color: '#e3453a', hidden: true });
paint(myLongTP, { name: 'Long Take Profit', style: 'dotted', color: '#36d957', hidden: true });
paint(myShortSL, { name: 'Short Stop Loss', style: 'dotted', color: '#e3453a', hidden: true });
paint(myShortTP, { name: 'Short Take Profit', style: 'dotted', color: '#36d957', hidden: true });

register_signal(myNewLong, 'Buy Signal');
register_signal(myNewShort, 'Sell Signal');
// Renamed to avoid a naming collision with the painted
// "NarrowStateLine" series above, which caused the engine error:
// output names must be unique across paint() and register_signal().
register_signal(myIsNarrowState, 'Narrow State Signal');