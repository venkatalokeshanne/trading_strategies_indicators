describe_indicator('NAS Style MTF ATR Strategy (3 TPs)', 'price');

// ===================== INPUTS =====================
const tabTrend = input.tab('Trend');
const myHTF = tabTrend.select('Higher Timeframe', '60', constants.time_frames);
const myStAtrLen = tabTrend.number('Supertrend ATR Length', 10, { min: 1, max: 100 });
const myStMult = tabTrend.number('Supertrend Multiplier', 3.0, { min: 0.1, max: 10 });
const smaRow = tabTrend.row();
const mySmaFastLen = smaRow.number('Fast SMA', 8, { min: 1, max: 500 });
const mySmaSlowLen = smaRow.number('Slow SMA', 9, { min: 1, max: 500 });

const tabRisk = input.tab('Risk');
const myAtrLen = tabRisk.number('ATR Length (TP/SL)', 10, { min: 1, max: 100 });
const myAtrRiskMult = tabRisk.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 10 });
const tpRow = tabRisk.row();
const myTp1MultR = tpRow.number('TP1 (R multiples)', 1.0, { min: 0.5, max: 5 });
const myTp2MultR = tpRow.number('TP2 (R multiples)', 2.0, { min: 0.5, max: 5 });
const myTp3MultR = tpRow.number('TP3 (R multiples)', 3.0, { min: 0.5, max: 5 });

// Note: this is a plain-JS reimplementation of Pine's stateful f_supertrend().
// Does not call any built-in indicator function inside the loop (ATR is
// precomputed outside), so it complies with the "no loops over indicators" rule.
// IMPORTANT: never use "new" (prohibited by the execution engine). Array(n)
// works identically to "new Array(n)" without using the "new" keyword.
function myComputeSupertrend(myPriceArr, myAtrArr, myMult) {
	const myN = myPriceArr.length;
	const myDirArr = Array(myN).fill(1);
	const myLineArr = Array(myN).fill(null);
	let myPrevLine = null;

	for (let myIndex = 0; myIndex < myN; myIndex += 1) {
		const myAtrValue = myAtrArr[myIndex];
		const myUpper = myPriceArr[myIndex] + myMult * myAtrValue;
		const myLower = myPriceArr[myIndex] - myMult * myAtrValue;
		let myDir;
		let myLine;

		if (myPriceArr[myIndex] > (myPrevLine != null ? myPrevLine : myLower)) {
			myDir = 1;
			myLine = Math.max(myLower, myPrevLine != null ? myPrevLine : myLower);
		}
		else {
			myDir = -1;
			myLine = Math.min(myUpper, myPrevLine != null ? myPrevLine : myUpper);
		}

		myDirArr[myIndex] = myDir;
		myLineArr[myIndex] = myLine;
		myPrevLine = myLine;
	}

	return { dir: myDirArr, line: myLineArr };
}

// ===================== LTF SUPERTREND =====================
const myLtfAtr = atr(high, low, close, myStAtrLen);
const myLtfSuper = myComputeSupertrend(close, myLtfAtr, myStMult);

// ===================== HTF SUPERTREND =====================
const myHtfData = await request.history(current.ticker, myHTF);
assert(!myHtfData.error, `Error fetching HTF data: "${myHtfData.error}"`);

const myHtfAtr = atr(myHtfData.high, myHtfData.low, myHtfData.close, myStAtrLen);
const myHtfSuper = myComputeSupertrend(myHtfData.close, myHtfAtr, myStMult);

// Land HTF dir/line onto the current chart's candles (constant interpolation,
// so this remains fully backtestable and non-repainting).
const myHtfDirLanded = land_points_onto_series(myHtfData.time, myHtfSuper.dir, time, 'le');
const myHtfLineLanded = land_points_onto_series(myHtfData.time, myHtfSuper.line, time, 'le');
const myHtfDir = interpolate_sparse_series(myHtfDirLanded, 'constant');
const myHtfLine = interpolate_sparse_series(myHtfLineLanded, 'constant');

// ===================== SMAs =====================
const mySmaFast = sma(close, mySmaFastLen);
const mySmaSlow = sma(close, mySmaSlowLen);

// ===================== CONDITIONS =====================
const myBullLTF = for_every(close, (_c, _p, _i) => myLtfSuper.dir[_i] === 1 && _c > myLtfSuper.line[_i]);
const myBearLTF = for_every(close, (_c, _p, _i) => myLtfSuper.dir[_i] === -1 && _c < myLtfSuper.line[_i]);
const myBullHTF = for_every(myHtfDir, _d => _d === 1);
const myBearHTF = for_every(myHtfDir, _d => _d === -1);

const myBull = for_every(myBullLTF, myBullHTF, (_bl, _bh) => _bl && _bh);
const myBear = for_every(myBearLTF, myBearHTF, (_bl, _bh) => _bl && _bh);

const myStrongBuy = for_every(myBull, mySmaFast, mySmaSlow, (_bull, _fast, _slow) => _bull && _fast >= _slow);
const myStrongSell = for_every(myBear, mySmaFast, mySmaSlow, (_bear, _fast, _slow) => _bear && _fast <= _slow);

const myLongEntry = myStrongBuy;
const myShortEntry = myStrongSell;

// ===================== ATR / RISK LEVELS (for reference only) =====================
const myAtr = atr(high, low, close, myAtrLen);
const myLongSL = sub(close, mult(myAtr, myAtrRiskMult));
const myLongR = sub(close, myLongSL);
const myShortSL = add(close, mult(myAtr, myAtrRiskMult));
const myShortR = sub(myShortSL, close);

const myLongTP1 = for_every(myLongEntry, close, myLongR, (_e, _c, _r) => (_e && _r > 0) ? _c + myTp1MultR * _r : null);
const myLongTP2 = for_every(myLongEntry, close, myLongR, (_e, _c, _r) => (_e && _r > 0) ? _c + myTp2MultR * _r : null);
const myLongTP3 = for_every(myLongEntry, close, myLongR, (_e, _c, _r) => (_e && _r > 0) ? _c + myTp3MultR * _r : null);

const myShortTP1 = for_every(myShortEntry, close, myShortR, (_e, _c, _r) => (_e && _r > 0) ? _c - myTp1MultR * _r : null);
const myShortTP2 = for_every(myShortEntry, close, myShortR, (_e, _c, _r) => (_e && _r > 0) ? _c - myTp2MultR * _r : null);
const myShortTP3 = for_every(myShortEntry, close, myShortR, (_e, _c, _r) => (_e && _r > 0) ? _c - myTp3MultR * _r : null);

// ===================== SIGNALS (for scanner / alerts / strategy) =====================
register_signal(myLongEntry, 'Strong Buy');
register_signal(myShortEntry, 'Strong Sell');
register_signal(myLongTP1.map(_v => _v != null), 'Long TP1 Set');
register_signal(myLongTP2.map(_v => _v != null), 'Long TP2 Set');
register_signal(myLongTP3.map(_v => _v != null), 'Long TP3 Set');
register_signal(myShortTP1.map(_v => _v != null), 'Short TP1 Set');
register_signal(myShortTP2.map(_v => _v != null), 'Short TP2 Set');
register_signal(myShortTP3.map(_v => _v != null), 'Short TP3 Set');

// ===================== PLOTTING =====================
const myLtfColor = for_every(close, (_c, _p, _i) => myLtfSuper.dir[_i] === 1 ? '#26A69A' : '#EF5350');
paint(myLtfSuper.line, { name: 'LTFSupertrend', color: myLtfColor, thickness: 2 });
paint(myHtfLine, { name: 'HTFSupertrend', color: '#4DA3FF', thickness: 2, style: 'line' });

const myBuyMarks = for_every(myLongEntry, low, (_e, _l) => _e ? _l : null);
const mySellMarks = for_every(myShortEntry, high, (_e, _h) => _e ? _h : null);

paint(myBuyMarks, { name: 'StrongBuy', style: 'labels_below', color: '#00E676' });
paint(mySellMarks, { name: 'StrongSell', style: 'labels_above', color: '#FF1744' });