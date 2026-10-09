describe_indicator('GXG Trend Engine', 'price');

// ─── Inputs ───
const myTab = input.tab('Settings');
const mySensFactor = myTab.number('Reaction Factor', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myAtrWindow = myTab.number('Volatility Window', 1, { min: 1, max: 100 });
const myUseHAFeed = myTab.boolean('Use Heikin Ashi Source', false);

// Pine's request.security(ticker.heikinashi(...)) is approximated here
// via request.history() with chart_type 'heikinashi' on the same ticker
// and resolution. This should match closely but may differ slightly in
// edge cases (e.g. real-time/unconfirmed bars).
const myHAData = await request.history(current.ticker, current.resolution, { chart_type: 'heikinashi' });
assert(!myHAData.error, 'Error fetching Heikin Ashi data: ' + myHAData.error);

const myHACloseLanded = land_points_onto_series(myHAData.time, myHAData.close, time, 'eq');
const myHACloseInterp = interpolate_sparse_series(myHACloseLanded, 'constant');

const myPriceFeed = myUseHAFeed ? myHACloseInterp : close;

// ─── Volatility band ───
const myVolatilityMeasure = atr(high, low, close, myAtrWindow);
const myBufferDistance = mult(myVolatilityMeasure, mySensFactor);

const myPriceFeedPrev = shift(myPriceFeed, 1);

// ─── Trail line (recursive) ───
const myTrailLine = for_every(myPriceFeed, myPriceFeedPrev, myBufferDistance, (_myPrice, _myPricePrev, _myBuffer, _myPrevTrail, _myIndex) => {
	const myPrevTrailVal = _myIndex === 0 ? 0 : (_myPrevTrail || 0);
	if (_myPrice > myPrevTrailVal && _myPricePrev > myPrevTrailVal) {
		return Math.max(myPrevTrailVal, _myPrice - _myBuffer);
	}
	else if (_myPrice < myPrevTrailVal && _myPricePrev < myPrevTrailVal) {
		return Math.min(myPrevTrailVal, _myPrice + _myBuffer);
	}
	else if (_myPrice > myPrevTrailVal) {
		return _myPrice - _myBuffer;
	}
	else {
		return _myPrice + _myBuffer;
	}
});

const myTrailLinePrev = shift(myTrailLine, 1);

// ─── Market bias (recursive state) ───
const myMarketBias = for_every(myPriceFeed, myPriceFeedPrev, myTrailLine, myTrailLinePrev, (_myPrice, _myPricePrev, _myTrail, _myTrailPrev, _myPrevBias) => {
	if (_myPricePrev < _myTrailPrev && _myPrice > _myTrail) {
		return 1;
	}
	else if (_myPricePrev > _myTrailPrev && _myPrice < _myTrail) {
		return -1;
	}
	else {
		return _myPrevBias || 0;
	}
});

// ─── Trigger / cross logic ───
// fastTrigger = ema(priceFeed, 1) is mathematically equal to priceFeed itself
const myFastTrigger = myPriceFeed;
const myFastTriggerPrev = myPriceFeedPrev;

const myBullCross = for_every(myFastTrigger, myFastTriggerPrev, myTrailLine, myTrailLinePrev, (_myFast, _myFastPrev, _myTrail, _myTrailPrev) => {
	return _myFast > _myTrail && _myFastPrev <= _myTrailPrev;
});

const myBearCross = for_every(myFastTrigger, myFastTriggerPrev, myTrailLine, myTrailLinePrev, (_myFast, _myFastPrev, _myTrail, _myTrailPrev) => {
	return _myTrail > _myFast && _myTrailPrev <= _myFastPrev;
});

const myLongSignal = for_every(myPriceFeed, myTrailLine, myBullCross, (_myPrice, _myTrail, _myBull) => {
	return _myPrice > _myTrail && _myBull;
});

const myShortSignal = for_every(myPriceFeed, myTrailLine, myBearCross, (_myPrice, _myTrail, _myBear) => {
	return _myPrice < _myTrail && _myBear;
});

const myIsBullZone = for_every(myPriceFeed, myTrailLine, (_myPrice, _myTrail) => _myPrice > _myTrail);
const myIsBearZone = for_every(myPriceFeed, myTrailLine, (_myPrice, _myTrail) => _myPrice < _myTrail);

// ─── Visuals ───
const myTrendColor = for_every(myMarketBias, _myBias => {
	if (_myBias === 1) return '#00ff00';
	if (_myBias === -1) return '#800000';
	return '#000080';
});

paint(myTrailLine, { name: 'GXG Adaptive Line', color: myTrendColor, thickness: 2, forceUsePriceAxis: true });

const myLongMarks = for_every(myLongSignal, _myLong => _myLong ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortSignal, _myShort => _myShort ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'GXG Long', style: 'labels_below', color: '#00ff00' });
paint(myShortMarks, { name: 'GXG Exit', style: 'labels_above', color: '#800000' });

const myCandleColors = for_every(myIsBullZone, myIsBearZone, (_myBull, _myBear) => {
	if (_myBull) return '#00ff00';
	if (_myBear) return '#800000';
	return null;
});
color_candles(myCandleColors);

// ─── Signals for scanner/alerts/strategy ───
register_signal(myLongSignal, 'GXG Long Entry');
register_signal(myShortSignal, 'GXG Exit Long');
register_signal(myIsBullZone, 'GXG Bull Zone');
register_signal(myIsBearZone, 'GXG Bear Zone');