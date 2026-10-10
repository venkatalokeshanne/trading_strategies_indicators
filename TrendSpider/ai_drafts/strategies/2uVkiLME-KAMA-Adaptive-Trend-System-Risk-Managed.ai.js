describe_indicator('KAMA Strategy (converted)', 'price');

// NOTE: TrendSpider custom indicators cannot place real orders,
// manage position size, or compute stop-loss orders like a Pine
// Script "strategy()" can. This conversion reproduces the KAMA
// math, the regime/momentum filters, and exposes the long/short
// trigger conditions as signals (for scanners/alerts), but it does
// NOT simulate equity, position sizing or stop-loss execution.

const myKamaTab = input.tab('KAMA Settings');
const myLookbackPeriod = myKamaTab.number('Length', 10, { min: 1, max: 500 });
const myPriceSource = myKamaTab.select('KAMA Source', 'close', constants.price_source_options);
const myFastLength = myKamaTab.number('Fast MA Length', 5, { min: 1, max: 500 });
const mySlowLength = myKamaTab.number('Slow MA Length', 50, { min: 1, max: 500 });

const myStrategyTab = input.tab('Strategy Settings');
const myOrderDirection = myStrategyTab.select('Order Direction', 'Long', ['Long', 'Short', 'Long and Short']);
const myKamaRisingPeriod = myStrategyTab.number('Rising Period', 10, { min: 1, max: 500 });
const myKamaFallingPeriod = myStrategyTab.number('Falling Period', 10, { min: 1, max: 500 });

const myRiskTab = input.tab('Risk Management and Filters');
const myFilterMaLen = myRiskTab.number('Regime Filter MA Length', 200, { min: 1, max: 1000 });
const myAtrPeriod = myRiskTab.number('ATR Period for Stop Loss', 14, { min: 1, max: 500 });
const myAtrMultiplier = myRiskTab.number('ATR Multiplier for Stop Loss', 2.5, { min: 0.1, max: 20 });
const myRsiPeriod = myRiskTab.number('RSI Period for Momentum', 14, { min: 1, max: 500 });
const myRsiMidline = myRiskTab.number('RSI Midline', 50, { min: 1, max: 99 });

const myPrice = market[myPriceSource];

// === KAMA computation, replicating Pine logic exactly ===
// price_change = |source - source[lookback]|
// sum_price_change = sum(|source - source[1]|, lookback)
// ER = price_change / sum_price_change
// SC = (ER*(fast-slow)+slow)^2
// sum := na(sum[1]) ? source : sum[1] + SC*(close - sum[1])
// Note: the Pine code uses "close" (not "source") inside the
// recursive update even though "source" feeds the rest of the
// formula; this is reproduced here exactly as written.
const myFastestAlpha = 2 / (myFastLength + 1);
const mySlowestAlpha = 2 / (mySlowLength + 1);

const mySourceShiftedLookback = shift(myPrice, myLookbackPeriod);
const mySourceShifted1 = shift(myPrice, 1);
const myPriceChange = for_every(myPrice, mySourceShiftedLookback, (_s, _sl) => (_sl === null || _sl === undefined) ? null : Math.abs(_s - _sl));
const myAbsDiff1 = for_every(myPrice, mySourceShifted1, (_s, _s1) => (_s1 === null || _s1 === undefined) ? null : Math.abs(_s - _s1));
const mySumPriceChange = sum(myAbsDiff1, myLookbackPeriod);

const myER = for_every(myPriceChange, mySumPriceChange, (_pc, _spc) => {
	if (_pc === null || _spc === null || _spc === 0) return null;
	return _pc / _spc;
});

const mySC = for_every(myER, _er => {
	if (_er === null) return null;
	const myRaw = _er * (myFastestAlpha - mySlowestAlpha) + mySlowestAlpha;
	return myRaw * myRaw;
});

const myKama = for_every(myPrice, close, mySC, (_source, _close, _sc, _prevValue, _index) => {
	if (_index === 0 || _prevValue === null || _prevValue === undefined) return _source;
	if (_sc === null) return _prevValue;
	return _prevValue + _sc * (_close - _prevValue);
});

// === Regime filter, ATR, RSI ===
const myFilterMa = sma(close, myFilterMaLen);
const myIsBullishRegime = for_every(close, myFilterMa, (_c, _f) => _c > _f);
const myIsBearishRegime = for_every(close, myFilterMa, (_c, _f) => _c < _f);

const myAtrValue = atr(high, low, close, myAtrPeriod);
const myRsiValue = rsi(close, myRsiPeriod);
const myIsBullishMomentum = for_every(myRsiValue, _r => _r > myRsiMidline);
const myIsBearishMomentum = for_every(myRsiValue, _r => _r < myRsiMidline);

// === ta.rising() / ta.falling() equivalents ===
// true when the series has strictly increased (or decreased) on
// every one of the last `period` bars.
function myComputeRising(mySeries, myPeriod) {
	return for_every(mySeries, (_v, _prevValue, _index) => {
		if (_index < myPeriod) return false;
		for (let myOffset = 0; myOffset < myPeriod; myOffset += 1) {
			if (!(mySeries[_index - myOffset] > mySeries[_index - myOffset - 1])) return false;
		}
		return true;
	});
}

function myComputeFalling(mySeries, myPeriod) {
	return for_every(mySeries, (_v, _prevValue, _index) => {
		if (_index < myPeriod) return false;
		for (let myOffset = 0; myOffset < myPeriod; myOffset += 1) {
			if (!(mySeries[_index - myOffset] < mySeries[_index - myOffset - 1])) return false;
		}
		return true;
	});
}

const myKamaRising = myComputeRising(myKama, myKamaRisingPeriod);
const myKamaFalling = myComputeFalling(myKama, myKamaFallingPeriod);

const myLongCondition = for_every(myKamaRising, myIsBullishRegime, myIsBullishMomentum, (_r, _breg, _bmom) => _r && _breg && _bmom);
const myShortCondition = for_every(myKamaFalling, myIsBearishRegime, myIsBearishMomentum, (_f, _breg, _bmom) => _f && _breg && _bmom);

// honor order direction setting for the entry signals
const myLongAllowed = myOrderDirection !== 'Short';
const myShortAllowed = myOrderDirection !== 'Long';

const myLongEntrySignal = for_every(myLongCondition, _l => _l && myLongAllowed);
const myShortEntrySignal = for_every(myShortCondition, _s => _s && myShortAllowed);

// alert triggers: KAMA color flips (rising starts / falling starts)
const myTurnGreenTrigger = for_every(myKamaRising, (_v, _prevValue, _index) => {
	if (_index === 0) return false;
	return _v && !myKamaRising[_index - 1];
});
const myTurnRedTrigger = for_every(myKamaFalling, (_v, _prevValue, _index) => {
	if (_index === 0) return false;
	return _v && !myKamaFalling[_index - 1];
});

// === Painting ===
const myKamaColor = for_every(myKama, close, (_k, _c) => _k > _c ? '#9cff87' : '#f9396a');

const myKamaLinePainted = paint(myKama, { name: 'KAMA', color: '#ffffff', thickness: 2 });
paint(myFilterMa, { name: 'RegimeFilterMA', color: 'orange', thickness: 2 });

color_cloud(myKama, close, '#9cff87', '#f9396a', 'KamaAboveClose', 'KamaBelowClose', 0.25);

// === Signals for scanners, alerts and strategy tester ===
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myTurnGreenTrigger, 'KAMA Turns Green');
register_signal(myTurnRedTrigger, 'KAMA Turns Red');