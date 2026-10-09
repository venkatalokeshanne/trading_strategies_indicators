describe_indicator('Apex PMT Bot (Pine Conversion)', 'price');

// =====================================================================
// NOTE: Pine Script `strategy.*` calls (position sizing, stop loss,
// trailing stop/offset, broker-side exits, alert_message delivery to a
// webhook/PMT) have no equivalent in the Custom JS API. This script
// reproduces the SIGNAL LOGIC exactly (same bars fire the same
// conditions), and exposes Long/Short/Exit conditions as register_signal()
// outputs usable in Scanners/Alerts/Strategy Tester. Actual order
// execution, stop-ticks, trailing offset math and PMT JSON payload
// delivery must be handled by TrendSpider's own Alert/Strategy actions,
// not by this indicator.
// =====================================================================

const myRiskTab = input.tab('Risk & PMT');
const myRiskGroup = myRiskTab.group('Risk Management');
const mySlTicks = myRiskGroup.number('Stop Loss (Ticks)', 400, { min: 1, max: 100000 });
const myTrailActiv = myRiskGroup.number('Trail Activation (Ticks)', 100, { min: 1, max: 100000 });
const myTrailOffset = myRiskGroup.number('Trail Offset (Ticks)', 50, { min: 1, max: 100000 });

const myPmtGroup = myRiskTab.group('PMT Messages (reference only, not sent by this script)');
const myPmtLongMsg = myPmtGroup.text('PMT Long JSON', '{"action": "buy", "symbol": "MNQM2026", "quantity": 2}', { hide_in_legend: true });
const myPmtShortMsg = myPmtGroup.text('PMT Short JSON', '{"action": "sell", "symbol": "MNQM2026", "quantity": 2}', { hide_in_legend: true });
const myPmtExitMsg = myPmtGroup.text('PMT Exit JSON', '{"action": "exit", "symbol": "MNQM2026"}', { hide_in_legend: true });

const myIndicatorsTab = input.tab('Indicators');
const myAdxThresholdRow = myIndicatorsTab.row();
const myRsiLength = myAdxThresholdRow.number('RSI Length', 14, { min: 1, max: 200 });
const myAdxThreshold = myAdxThresholdRow.number('ADX Threshold', 20, { min: 1, max: 100 });

const myMaRow = myIndicatorsTab.row();
const mySmaLength = myMaRow.number('SMA Length (Trend)', 20, { min: 1, max: 500 });
const myVolSmaLength = myMaRow.number('Volume SMA Length', 20, { min: 1, max: 500 });

// =====================================================================
// 2. INDICATORS
// =====================================================================
const myRsiVal = rsi(close, myRsiLength);

const myMacdLine = sub(ema(close, 12), ema(close, 26));
const mySignalLine = ema(myMacdLine, 9);

const myAdxObject = indicators.adx(14);
const myAdxVal = myAdxObject.adx;

const myAtrVal = atr(high, low, close, 14);
const myVolSma = sma(volume, myVolSmaLength);
const myHighVolume = for_every(volume, myVolSma, (_v, _vs) => _v > _vs);

const myCloseSma = sma(close, mySmaLength);

// =====================================================================
// 3. STRUCTURAL PATTERNS
// =====================================================================
const myHighShift2 = shift(high, 2);
const myLowShift2 = shift(low, 2);
const myCloseShift1 = shift(close, 1);
const myOpenShift1 = shift(open, 1);

const myBullishFVG = for_every(low, myHighShift2, myCloseShift1, myOpenShift1,
	(_l, _h2, _c1, _o1) => _l > _h2 && _c1 > _o1
);

const myBearishFVG = for_every(high, myLowShift2, myCloseShift1, myOpenShift1,
	(_h, _l2, _c1, _o1) => _h < _l2 && _c1 < _o1
);

// crossover / crossunder of macd vs signal
const myMacdPrev = shift(myMacdLine, 1);
const mySignalPrev = shift(mySignalLine, 1);

const myCrossOver = for_every(myMacdLine, mySignalLine, myMacdPrev, mySignalPrev,
	(_m, _s, _mp, _sp) => _m > _s && _mp <= _sp
);

const myCrossUnder = for_every(myMacdLine, mySignalLine, myMacdPrev, mySignalPrev,
	(_m, _s, _mp, _sp) => _m < _s && _mp >= _sp
);

const myBullReversal = for_every(myCrossOver, myRsiVal, (_co, _r) => _co && _r < 40);
const myBearReversal = for_every(myCrossUnder, myRsiVal, (_cu, _r) => _cu && _r > 60);

const myBullFlag = for_every(close, myCloseSma, myHighVolume, myBullishFVG,
	(_c, _sma, _hv, _bfvg) => _c > _sma && _hv && _bfvg
);

const myBearFlag = for_every(close, myCloseSma, myHighVolume, myBearishFVG,
	(_c, _sma, _hv, _bfvg) => _c < _sma && _hv && _bfvg
);

// =====================================================================
// 4. EXECUTION CONDITIONS (signals only, no position/order simulation)
// =====================================================================
const myLongCond = for_every(myBullishFVG, myBullReversal, myBullFlag, myHighVolume, myAdxVal,
	(_bfvg, _brev, _bflag, _hv, _adx) => (_bfvg || _brev || _bflag) && _hv && _adx > myAdxThreshold
);

const myShortCond = for_every(myBearishFVG, myBearReversal, myBearFlag, myHighVolume, myAdxVal,
	(_bfvg, _brev, _bflag, _hv, _adx) => (_bfvg || _brev || _bflag) && _hv && _adx > myAdxThreshold
);

// Approximate exit signal: fires whenever an opposite entry condition
// appears. This is NOT the same as the Pine strategy.exit() stop/trail
// logic, which depends on live position state and tick-based price
// distances that this engine cannot simulate.
const myExitSignal = for_every(myLongCond, myShortCond, (_l, _s) => _l || _s);

register_signal(myLongCond, 'Long Entry');
register_signal(myShortCond, 'Short Entry');
register_signal(myExitSignal, 'Exit (Approximate)');

// =====================================================================
// 3b. VISUALS - FVG background coloring
// =====================================================================
const myCandleColors = for_every(myBullishFVG, myBearishFVG, (_b, _s) => {
	if (_b) return 'rgba(0,200,0,0.15)';
	if (_s) return 'rgba(200,0,0,0.15)';
	return null;
});
color_candles(myCandleColors);

// =====================================================================
// 5. DASHBOARD
// =====================================================================
const myLastIndex = close.length - 1;
const myRsiText = isFinite(myRsiVal[myLastIndex]) ? myRsiVal[myLastIndex].toFixed(2) : '0.00';
const myAdxText = isFinite(myAdxVal[myLastIndex]) ? myAdxVal[myLastIndex].toFixed(2) : '0.00';
const myMacdText = isFinite(myMacdLine[myLastIndex]) ? myMacdLine[myLastIndex].toFixed(2) : '0.00';
const myAtrText = isFinite(myAtrVal[myLastIndex]) ? myAtrVal[myLastIndex].toFixed(2) : '0.00';

paint_overlay('ApexBotDashboard', { position: 'bottom_right' }, {
	rows: [{
		cells: [{ text: 'THE GREATEST BOT EVER MADE', color: 'white' }]
	}, {
		cells: [{ text: 'Risk Mgmt:', color: 'gray' }, { text: mySlTicks + ' Ticks SL', color: 'white' }]
	}, {
		cells: [{ text: 'Take Profit:', color: 'gray' }, { text: 'Auto Trail (not simulated)', color: 'white' }]
	}, {
		cells: [{ text: 'RSI | ADX:', color: 'gray' }, { text: myRsiText + ' | ' + myAdxText, color: 'white' }]
	}, {
		cells: [{ text: 'MACD | ATR:', color: 'gray' }, { text: myMacdText + ' | ' + myAtrText, color: 'white' }]
	}]
});