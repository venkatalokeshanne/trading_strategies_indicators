describe_indicator('Penroute Trend Score', 'price');

// ---- inputs, organized in tabs
const adxTab = input.tab('ADX');
const adxLen = adxTab.number('ADX length', 14, { min: 1, max: 200 });
const adxTh = adxTab.number('ADX above', 25, { min: 0, max: 100 });

const effTab = input.tab('Efficiency');
const erLen = effTab.number('Efficiency lookback', 20, { min: 1, max: 500 });
const erTh = effTab.number('Efficiency above', 0.55, { min: 0, max: 1, step: 0.01 });

const emaTab = input.tab('EMA');
const emaLen = emaTab.number('EMA length', 50, { min: 1, max: 1000 });
const emaLook = emaTab.number('EMA closes lookback', 10, { min: 1, max: 500 });
const emaNeed = emaTab.number('Closes needed same side', 8, { min: 1, max: 500 });

const sweepTab = input.tab('Sweep');
const sweepLook = sweepTab.number('Sweep lookback', 20, { min: 1, max: 500 });
const sweepTh = sweepTab.number('Reversion rate below', 0.40, { min: 0, max: 1, step: 0.01 });

const atrTab = input.tab('ATR');
const atrFast = atrTab.number('ATR fast', 5, { min: 1, max: 500 });
const atrSlow = atrTab.number('ATR slow', 20, { min: 1, max: 500 });
const atrTh = atrTab.number('ATR ratio above', 1.30, { min: 0, max: 10, step: 0.05 });

// ---- 1. ADX (DMI/ADX via built-in indicators.adx)
const myAdxObject = indicators.adx(adxLen);
const myAdxVal = myAdxObject.adx;
const myC1 = for_every(myAdxVal, _a => _a > adxTh);

// ---- 2. directional efficiency
const myNetMove = for_every(close, shift(close, erLen), (_c, _cPrev) => Math.abs(_c - _cPrev));
const myAbsDiff = for_every(close, shift(close, 1), (_c, _cPrev) => Math.abs(_c - _cPrev));
const myPathMove = sum(myAbsDiff, erLen);
const myEffRatio = for_every(myNetMove, myPathMove, (_net, _path) => _path > 0 ? _net / _path : 0.0);
const myC2 = for_every(myEffRatio, _e => _e > erTh);

// ---- 3. closes vs EMA
const myEmaVal = ema(close, emaLen);
const myAboveFlag = for_every(close, myEmaVal, (_c, _e) => _c > _e ? 1 : 0);
const myAboveSum = sum(myAboveFlag, emaLook);
const mySameSide = for_every(myAboveSum, _above => Math.max(_above, emaLook - _above));
const myC3 = for_every(mySameSide, _s => _s >= emaNeed);

// ---- 4. sweep reversion rate
const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);
const myBrokeHigh = for_every(high, myPrevHigh, (_h, _ph) => _h > _ph);
const myBrokeLow = for_every(low, myPrevLow, (_l, _pl) => _l < _pl);
const myBroke = for_every(myBrokeHigh, myBrokeLow, (_bh, _bl) => _bh || _bl);
const myReverted = for_every(myBrokeHigh, myBrokeLow, close, myPrevHigh, myPrevLow, (_bh, _bl, _c, _ph, _pl) => {
	if (_bh && _bl) return _c <= _ph && _c >= _pl;
	if (_bh) return _c <= _ph;
	if (_bl) return _c >= _pl;
	return false;
});
const myBreaksFlag = for_every(myBroke, _b => _b ? 1 : 0);
const myRevertedFlag = for_every(myReverted, _r => _r ? 1 : 0);
const myBreaksSum = sum(myBreaksFlag, sweepLook);
const myRevertsSum = sum(myRevertedFlag, sweepLook);
const myRevRate = for_every(myBreaksSum, myRevertsSum, (_breaks, _reverts) => _breaks > 0 ? _reverts / _breaks : null);
const myC4 = for_every(myRevRate, myBreaksSum, (_rr, _breaks) => _rr !== null && _breaks >= 5 && _rr < sweepTh);

// ---- 5. ATR ratio
const myAtrFastVal = atr(high, low, close, atrFast);
const myAtrSlowVal = atr(high, low, close, atrSlow);
const myAtrRatio = for_every(myAtrFastVal, myAtrSlowVal, (_f, _s) => _s > 0 ? _f / _s : 0.0);
const myC5 = for_every(myAtrRatio, _ar => _ar > atrTh);

// ---- score
const myScore = for_every(myC1, myC2, myC3, myC4, myC5, (_c1, _c2, _c3, _c4, _c5) =>
	(_c1 ? 1 : 0) + (_c2 ? 1 : 0) + (_c3 ? 1 : 0) + (_c4 ? 1 : 0) + (_c5 ? 1 : 0)
);
const myTrendFlag = for_every(myScore, _s => _s >= 3);
const myRangeFlag = for_every(myScore, _s => _s <= 1);
const myMixedFlag = for_every(myScore, _s => _s > 1 && _s < 3);

// ---- register signals for scanning / alerts / strategies
register_signal(myC1, 'ADX above threshold');
register_signal(myC2, 'Directional efficiency above threshold');
register_signal(myC3, 'Closes same side of EMA');
register_signal(myC4, 'Sweep reversion rate below threshold');
register_signal(myC5, 'ATR ratio above threshold');
register_signal(myTrendFlag, 'Trend verdict');
register_signal(myRangeFlag, 'Range verdict');
register_signal(myMixedFlag, 'Mixed verdict');

// ---- paint EMA line
paint(myEmaVal, { name: 'EMA50', color: 'gray', thickness: 1 });

// ---- last bar values, for the summary table
const myLastIndex = close.length - 1;
const myLastAdx = myAdxVal[myLastIndex];
const myLastEff = myEffRatio[myLastIndex];
const myLastSameSide = mySameSide[myLastIndex];
const myLastRevRate = myRevRate[myLastIndex];
const myLastBreaks = myBreaksSum[myLastIndex];
const myLastAtrRatio = myAtrRatio[myLastIndex];
const myLastScore = myScore[myLastIndex];
const myLastC1 = myC1[myLastIndex];
const myLastC2 = myC2[myLastIndex];
const myLastC3 = myC3[myLastIndex];
const myLastC4 = myC4[myLastIndex];
const myLastC5 = myC5[myLastIndex];

const myVerdict = myLastScore >= 3 ? 'TREND' : (myLastScore <= 1 ? 'RANGE' : 'MIXED');
const myMethod = myLastScore >= 3 ? 'Sweep and continuation' : (myLastScore <= 1 ? 'Reversal, original' : 'No clear read');
const myVerdictColor = myLastScore >= 3 ? '#96660D' : (myLastScore <= 1 ? '#2F6F62' : '#98A2AC');
const myBgColor = 'rgba(128,128,128,0.1)';
const myGrayText = 'gray';
const myWhiteText = 'white';

const myAdxText = myLastAdx === null || myLastAdx === undefined ? 'n/a' : myLastAdx.toFixed(1);
const myEffText = myLastEff === null || myLastEff === undefined ? 'n/a' : myLastEff.toFixed(2);
const mySameSideText = (myLastSameSide === null || myLastSameSide === undefined ? 'n/a' : myLastSameSide) + '/' + emaLook;
const myRevRateText = (myLastRevRate === null || myLastRevRate === undefined) ? 'n/a' : (Math.round(myLastRevRate * 100) + '% (' + myLastBreaks + ')');
const myAtrRatioText = myLastAtrRatio === null || myLastAtrRatio === undefined ? 'n/a' : myLastAtrRatio.toFixed(2);

const myIsDaily = current.resolution === 'D';

// ---- summary table overlay
paint_overlay('PenrouteTrendScorePanel', { position: 'top_right' }, {
	rows: [
		{
			cells: [
				{ text: current.ticker + '  ' + myVerdict, color: myWhiteText, background_color: myVerdictColor },
				{ text: myLastScore + '/5', color: myWhiteText, background_color: myVerdictColor },
				{ text: '', background_color: myVerdictColor }
			]
		},
		{
			cells: [
				{ text: 'ADX', color: myGrayText, background_color: myBgColor },
				{ text: myAdxText, color: myGrayText, background_color: myBgColor },
				{ text: myLastC1 ? 'YES' : 'no', color: myLastC1 ? myVerdictColor : myGrayText, background_color: myBgColor }
			]
		},
		{
			cells: [
				{ text: 'Efficiency', color: myGrayText, background_color: myBgColor },
				{ text: myEffText, color: myGrayText, background_color: myBgColor },
				{ text: myLastC2 ? 'YES' : 'no', color: myLastC2 ? myVerdictColor : myGrayText, background_color: myBgColor }
			]
		},
		{
			cells: [
				{ text: 'Closes vs EMA', color: myGrayText, background_color: myBgColor },
				{ text: mySameSideText, color: myGrayText, background_color: myBgColor },
				{ text: myLastC3 ? 'YES' : 'no', color: myLastC3 ? myVerdictColor : myGrayText, background_color: myBgColor }
			]
		},
		{
			cells: [
				{ text: 'Sweep reversion', color: myGrayText, background_color: myBgColor },
				{ text: myRevRateText, color: myGrayText, background_color: myBgColor },
				{ text: myLastC4 ? 'YES' : 'no', color: myLastC4 ? myVerdictColor : myGrayText, background_color: myBgColor }
			]
		},
		{
			cells: [
				{ text: 'ATR ratio', color: myGrayText, background_color: myBgColor },
				{ text: myAtrRatioText, color: myGrayText, background_color: myBgColor },
				{ text: myLastC5 ? 'YES' : 'no', color: myLastC5 ? myVerdictColor : myGrayText, background_color: myBgColor }
			]
		},
		{
			cells: [
				{ text: 'Method', color: myGrayText, background_color: myBgColor },
				{ text: myMethod, color: myVerdictColor, background_color: myBgColor },
				{ text: '', background_color: myBgColor }
			]
		},
		{
			cells: myIsDaily ? [{ text: '' }] : [
				{ text: 'NOT DAILY CHART', color: myWhiteText, background_color: '#A32E2E' },
				{ text: '', background_color: '#A32E2E' },
				{ text: '', background_color: '#A32E2E' }
			]
		}
	]
});