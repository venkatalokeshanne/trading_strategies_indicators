// ====================================================================
// EXPERIMENT / APPROXIMATION NOTICE:
// TradingView's original script pulls on-chain data via the special
// CoinMetrics symbols "BTC_MARKETCAP" and "BTC_MARKETCAPREAL" through
// request.security(). TrendSpider's Custom JS API has no equivalent
// data source (no on-chain market cap / realized cap feed is exposed
// via request.history, request.fundamental or any other request.*
// call). It is therefore impossible to reproduce the Pine script
// EXACTLY, since the underlying data itself cannot be fetched.
//
// As a best-effort proxy only, this version uses:
//   marketCap   -> close price of current.ticker (NOT real market cap)
//   realizedCap -> a long-window SMA of close (NOT real realized cap)
// This will NOT match the original indicator's values or signal bars.
// Treat this purely as an experimental structural port of the logic.
// ====================================================================
describe_indicator('CTZ MVRV Z-Score (approximated)', 'lower');

const myDisplayTab = input.tab('Data / Display');
const myShowCaps = myDisplayTab.boolean('Show Market and Realized Cap (log)', true);
const myShowMvrv = myDisplayTab.boolean('Show MVRV Ratio instead of Z-Score', false);
const myRealizedLength = myDisplayTab.number('Realized Cap Proxy SMA Length', 365, { min: 10, max: 1000 });

const myZoneTab = input.tab('Zone Levels');
const myTopTrig = myZoneTab.number('Top Zone Z upper', 6.85, { min: -50, max: 50, step: 0.05 });
const myTopLo = myZoneTab.number('Top Zone Z lower', 5.5, { min: -50, max: 50, step: 0.05 });
const myBotTrig = myZoneTab.number('Bottom Zone Z upper', 0.1, { min: -50, max: 50, step: 0.05 });
const myBotLo = myZoneTab.number('Bottom Zone Z lower', -0.5, { min: -50, max: 50, step: 0.05 });

// Proxy series (NOT real market/realized cap, see notice above)
const myMarketCap = close;
const myRealizedCap = sma(close, myRealizedLength);

const myDataOk = for_every(myMarketCap, myRealizedCap, (_mc, _rc) => _mc !== null && _rc !== null && !isNaN(_mc) && !isNaN(_rc));

// MVRV ratio
const myMvrv = for_every(myMarketCap, myRealizedCap, myDataOk, (_mc, _rc, _ok) => _ok ? _mc / _rc : null);

// Cumulative mean/std of marketCap, computed sequentially (matches Pine's running var/sum logic).
// We can't reference the output series from within its own for_every callback
// (that caused the "Cannot access before initialization" error), so these
// running sums are built with a plain loop instead.
const mySumMC = series_of(0);
const mySumMC2 = series_of(0);
const myCountMC = series_of(0);

for (let myIndex = 0; myIndex < myMarketCap.length; myIndex += 1) {
	const myPrevSum = myIndex > 0 ? mySumMC[myIndex - 1] : 0;
	const myPrevSum2 = myIndex > 0 ? mySumMC2[myIndex - 1] : 0;
	const myPrevCount = myIndex > 0 ? myCountMC[myIndex - 1] : 0;

	if (myDataOk[myIndex]) {
		mySumMC[myIndex] = myPrevSum + myMarketCap[myIndex];
		mySumMC2[myIndex] = myPrevSum2 + myMarketCap[myIndex] * myMarketCap[myIndex];
		myCountMC[myIndex] = myPrevCount + 1;
	}
	else {
		mySumMC[myIndex] = myPrevSum;
		mySumMC2[myIndex] = myPrevSum2;
		myCountMC[myIndex] = myPrevCount;
	}
}

const myZscore = for_every(myMarketCap, myRealizedCap, myDataOk, mySumMC, mySumMC2, myCountMC, (_mc, _rc, _ok, _sum, _sum2, _n) => {
	if (!_ok || _n <= 1) {
		return null;
	}
	const myVarMC = (_sum2 - _sum * _sum / _n) / (_n - 1);
	if (!(myVarMC > 0)) {
		return null;
	}
	const myStdMC = Math.sqrt(myVarMC);
	if (!(myStdMC > 0)) {
		return null;
	}
	return (_mc - _rc) / myStdMC;
});

const myPlotVal = myShowMvrv ? myMvrv : myZscore;
paint(myPlotVal, { name: 'MVRVZScore', color: '#FF9800', thickness: 2 });

const myTopUpperSeries = myShowMvrv ? constants.empty_series : horizontal_line(myTopTrig);
const myTopLowerSeries = myShowMvrv ? constants.empty_series : horizontal_line(myTopLo);
const myBotUpperSeries = myShowMvrv ? constants.empty_series : horizontal_line(myBotTrig);
const myBotLowerSeries = myShowMvrv ? constants.empty_series : horizontal_line(myBotLo);

const myTopUpperPainted = paint(myTopUpperSeries, { name: 'TopUpper', color: 'rgba(244,67,54,0.4)' });
const myTopLowerPainted = paint(myTopLowerSeries, { name: 'TopLower', color: 'rgba(244,67,54,0.4)' });
fill(myTopUpperPainted, myTopLowerPainted, 'red', 0.15);

const myBotUpperPainted = paint(myBotUpperSeries, { name: 'BottomUpper', color: 'rgba(76,175,80,0.4)' });
const myBotLowerPainted = paint(myBotLowerSeries, { name: 'BottomLower', color: 'rgba(76,175,80,0.4)' });
fill(myBotUpperPainted, myBotLowerPainted, 'green', 0.2);

paint(horizontal_line(myShowMvrv ? 1.0 : 0.0), { name: 'ZeroParity', color: 'gray', style: 'dotted' });

function myLog10(_x) {
	return (_x !== null && !isNaN(_x) && _x > 0) ? Math.log(_x) / Math.log(10) : null;
}

const myMcLog = for_every(myMarketCap, _mc => myLog10(_mc));
const myRcLog = for_every(myRealizedCap, _rc => myLog10(_rc));

paint(myShowCaps ? myMcLog : constants.empty_series, { name: 'MarketCapLog', color: 'black', forceUsePriceAxis: false });
paint(myShowCaps ? myRcLog : constants.empty_series, { name: 'RealizedCapLog', color: 'blue', forceUsePriceAxis: false });

const myBelowReal = for_every(myMarketCap, myRealizedCap, myDataOk, (_mc, _rc, _ok) => _ok && _mc < _rc);
const myCandleColors = for_every(myBelowReal, _b => _b ? 'rgba(76,175,80,0.1)' : null);
color_candles(myCandleColors);

const myInTop = for_every(myZscore, _z => _z !== null && _z >= myTopTrig);
const myInBot = for_every(myZscore, myBelowReal, (_z, _b) => (_z !== null && _z <= myBotTrig) || _b);

const myTopSignal = for_every(myInTop, (_in, _prev, _idx) => {
	const myPrevIn = _idx > 0 ? myInTop[_idx - 1] : false;
	return _in && !myPrevIn;
});

const myBotSignal = for_every(myInBot, (_in, _prev, _idx) => {
	const myPrevIn = _idx > 0 ? myInBot[_idx - 1] : false;
	return _in && !myPrevIn;
});

const myTopMarks = for_every(myTopSignal, high, (_sig, _h) => _sig ? _h : null);
const myBotMarks = for_every(myBotSignal, low, (_sig, _l) => _sig ? _l : null);

paint(myTopMarks, { name: 'TopSignal', style: 'labels_above', color: 'red' });
paint(myBotMarks, { name: 'BottomSignal', style: 'labels_below', color: 'green' });

register_signal(myTopSignal, 'MVRV Top Signal');
register_signal(myBotSignal, 'MVRV Bottom Signal');
register_signal(myBelowReal, 'Below Realized Cap');
register_signal(myDataOk, 'Data Available');