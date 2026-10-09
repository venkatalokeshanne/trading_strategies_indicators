describe_indicator('EMA Crosses Strategy', 'price');

// EMA1 settings
const ema1Tab = input.group('EMA1 Settings');
const myEma1Length = ema1Tab.number('EMA1 Length', 9, { min: 1, max: 500 });
const myEma1Source = ema1Tab.select('EMA1 Source', 'close', constants.price_source_options);

// EMA2 settings
const ema2Tab = input.group('EMA2 Settings');
const myEma2Length = ema2Tab.number('EMA2 Length', 26, { min: 1, max: 500 });
const myEma2Source = ema2Tab.select('EMA2 Source', 'close', constants.price_source_options);

// Risk management settings (points, i.e. price units)
const riskTab = input.group('Risk Management');
const mySlPoints = riskTab.number('Stop Loss (Points)', 20, { min: 0 });
const myTpPoints = riskTab.number('Take Profit (Points)', 40, { min: 0 });

const myEma1 = ema(market[myEma1Source], myEma1Length);
const myEma2 = ema(market[myEma2Source], myEma2Length);

paint(myEma1, { name: 'EMA1', color: 'green', thickness: 2 });
paint(myEma2, { name: 'EMA2', color: 'orange', thickness: 2 });

// crossover / crossunder detection, replicating ta.crossover / ta.crossunder
const myBuyCondition = for_every(myEma1, myEma2, (_e1, _e2, _prev, _idx) => {
	if (_idx < 1) return false;
	return myEma1[_idx] > myEma2[_idx] && myEma1[_idx - 1] <= myEma2[_idx - 1];
});

const mySellCondition = for_every(myEma1, myEma2, (_e1, _e2, _prev, _idx) => {
	if (_idx < 1) return false;
	return myEma1[_idx] < myEma2[_idx] && myEma1[_idx - 1] >= myEma2[_idx - 1];
});

// Simulate strategy.position_size to know when entries/exits are allowed,
// since position state (long/short/flat) is not natively tracked by the
// Custom JS API. This replicates "if buyCondition and position_size <= 0"
// and "if sellCondition and position_size >= 0" logic from the Pine script.
const myPositionState = series_of(0);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myEntryPrice = series_of(null);
const myLongSL = series_of(null);
const myLongTP = series_of(null);
const myShortSL = series_of(null);
const myShortTP = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevState = myIndex > 0 ? myPositionState[myIndex - 1] : 0;
	const myPrevEntryPrice = myIndex > 0 ? myEntryPrice[myIndex - 1] : null;

	let myState = myPrevState;
	let myEntry = myPrevEntryPrice;
	let myDidBuy = false;
	let myDidSell = false;

	if (myBuyCondition[myIndex] && myPrevState <= 0) {
		myState = 1;
		myEntry = close[myIndex];
		myDidBuy = true;
	}
	else if (mySellCondition[myIndex] && myPrevState >= 0) {
		myState = -1;
		myEntry = close[myIndex];
		myDidSell = true;
	}

	// Check stop loss / take profit exits based on current bar's high/low
	if (myState === 1 && myEntry !== null) {
		const myStop = myEntry - mySlPoints;
		const myLimit = myEntry + myTpPoints;
		if (low[myIndex] <= myStop || high[myIndex] >= myLimit) {
			myState = 0;
			myEntry = null;
		}
	}
	else if (myState === -1 && myEntry !== null) {
		const myStop = myEntry + mySlPoints;
		const myLimit = myEntry - myTpPoints;
		if (high[myIndex] >= myStop || low[myIndex] <= myLimit) {
			myState = 0;
			myEntry = null;
		}
	}

	myPositionState[myIndex] = myState;
	myEntryPrice[myIndex] = myEntry;
	myBuySignal[myIndex] = myDidBuy;
	mySellSignal[myIndex] = myDidSell;

	myLongSL[myIndex] = myEntry !== null && myState === 1 ? myEntry - mySlPoints : null;
	myLongTP[myIndex] = myEntry !== null && myState === 1 ? myEntry + myTpPoints : null;
	myShortSL[myIndex] = myEntry !== null && myState === -1 ? myEntry + mySlPoints : null;
	myShortTP[myIndex] = myEntry !== null && myState === -1 ? myEntry - myTpPoints : null;
}

// Register signals for use in scanners, alerts and strategy tester
register_signal(myBuySignal, 'Buy Entry');
register_signal(mySellSignal, 'Sell Entry');
register_signal(for_every(myBuySignal, mySellSignal, myPositionState, (_b, _s, _pos, _prev, _idx) => _idx > 0 && myPositionState[_idx] === 0 && myPositionState[_idx - 1] === 1), 'Long Exit');
register_signal(for_every(myBuySignal, mySellSignal, myPositionState, (_b, _s, _pos, _prev, _idx) => _idx > 0 && myPositionState[_idx] === 0 && myPositionState[_idx - 1] === -1), 'Short Exit');