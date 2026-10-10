describe_indicator('2x Universal Lines LionTrader', 'price');

// -----------------------------------------------------------------
// General direction setting
// -----------------------------------------------------------------
const myDirection = input.select('Direction', 'both', ['both', 'short', 'long']);

// -----------------------------------------------------------------
// Line 1 settings
// -----------------------------------------------------------------
const myTab1 = input.tab('Line 1');
const myLineType1 = myTab1.select('Line Type 1', 'EMA', ['SMA', 'EMA', 'WMA', 'RMA', 'SMMA', 'VWMA', 'HMA', 'ALMA', 'LSMA', 'DEMA', 'TEMA', 'KAMA', 'ZLEMA', 'TMA', 'McGinley', 'VWAP', 'PriceOnly']);
const mySource1 = myTab1.select('Source 1', 'close', constants.price_source_options);
const myLength1 = myTab1.number('Length 1', 21, { min: 1, max: 500 });
const myAlmaOffset1 = myTab1.number('ALMA Offset 1', 0.85, { min: 0, max: 1, step: 0.05 });
const myAlmaSigma1 = myTab1.number('ALMA Sigma 1', 6, { min: 0.1, max: 50, step: 1 });

// -----------------------------------------------------------------
// Line 2 settings
// -----------------------------------------------------------------
const myTab2 = input.tab('Line 2');
const myLineType2 = myTab2.select('Line Type 2', 'SMA', ['SMA', 'EMA', 'WMA', 'RMA', 'SMMA', 'VWMA', 'HMA', 'ALMA', 'LSMA', 'DEMA', 'TEMA', 'KAMA', 'ZLEMA', 'TMA', 'McGinley', 'VWAP', 'PriceOnly']);
const mySource2 = myTab2.select('Source 2', 'close', constants.price_source_options);
const myLength2 = myTab2.number('Length 2', 50, { min: 1, max: 500 });
const myAlmaOffset2 = myTab2.number('ALMA Offset 2', 0.85, { min: 0, max: 1, step: 0.05 });
const myAlmaSigma2 = myTab2.number('ALMA Sigma 2', 6, { min: 0.1, max: 50, step: 1 });

// -----------------------------------------------------------------
// Custom math helpers (ported from the Pine script)
// -----------------------------------------------------------------

// DEMA = 2*EMA - EMA(EMA)
function myComputeDema(mySeries, myLen) {
	const myE1 = ema(mySeries, myLen);
	return sub(mult(myE1, 2), ema(myE1, myLen));
}

// ZLEMA = EMA(src + (src - src[lag]))
function myComputeZlema(mySeries, myLen) {
	const myLag = Math.round((myLen - 1) / 2);
	const myEmaData = add(mySeries, sub(mySeries, shift(mySeries, myLag)));
	return ema(myEmaData, myLen);
}

// TMA = SMA(SMA(src, halfLen), halfLen)
function myComputeTma(mySeries, myLen) {
	const myHalfLen = Math.round((myLen + 1) / 2);
	return sma(sma(mySeries, myHalfLen), myHalfLen);
}

// McGinley Dynamic (recursive formula from the Pine script)
function myComputeMcginley(mySeries, myLen) {
	return for_every(mySeries, (mySrcValue, myPrevValue, myIndex) => {
		if (myIndex === 0 || myPrevValue === null || myPrevValue === undefined || !isFinite(myPrevValue)) {
			return mySrcValue;
		}
		const myRatio = mySrcValue / myPrevValue;
		return myPrevValue + (mySrcValue - myPrevValue) / (myLen * Math.pow(myRatio, 4));
	});
}

// Builds a line based on the selected type, mirroring get_line() in Pine
function myGetLine(myType, mySeries, myLen, myAlmaOffset, myAlmaSigma) {
	switch (myType) {
		case 'SMA': return sma(mySeries, myLen);
		case 'EMA': return ema(mySeries, myLen);
		case 'WMA': return wma(mySeries, myLen);
		case 'RMA': return wildma(mySeries, myLen);
		case 'SMMA': return wildma(mySeries, myLen);
		case 'VWMA': return vwma(mySeries, myLen);
		case 'HMA': return hullma(mySeries, myLen);
		case 'ALMA': return alma(mySeries, myLen, myAlmaOffset, myAlmaSigma);
		case 'LSMA': return linreg(mySeries, myLen);
		case 'DEMA': return myComputeDema(mySeries, myLen);
		case 'TEMA': return indicators.tema(mySeries, myLen);
		// KAMA: er fast=2/31, slow=2/31 constants in Pine correspond to
		// fast length 2 and slow length 30 in the built-in kama() formula.
		case 'KAMA': return kama(mySeries, myLen, 2, 30);
		case 'ZLEMA': return myComputeZlema(mySeries, myLen);
		case 'TMA': return myComputeTma(mySeries, myLen);
		case 'McGinley': return myComputeMcginley(mySeries, myLen);
		// VWAP: Pine's ta.vwap resets every session (day) by default.
		// This platform's vwap() does not support automatic session
		// resets off a custom source the same way, so this is
		// approximated as a VWAP computed from the first candle onward.
		case 'VWAP': return vwap(mySeries, volume, 0);
		case 'PriceOnly': return mySeries;
		default: return mySeries;
	}
}

const myPrice1 = market[mySource1];
const myPrice2 = market[mySource2];

const myLine1 = myGetLine(myLineType1, myPrice1, myLength1, myAlmaOffset1, myAlmaSigma1);
const myLine2 = myGetLine(myLineType2, myPrice2, myLength2, myAlmaOffset2, myAlmaSigma2);

// -----------------------------------------------------------------
// Crossover / crossunder detection
// -----------------------------------------------------------------
const myDiff = sub(myLine1, myLine2);
const myDiffPrev = shift(myDiff, 1);

const myCrossUp = for_every(myDiff, myDiffPrev, (myD, myDPrev) => myDPrev !== null && myD !== null && myD > 0 && myDPrev <= 0);
const myCrossDown = for_every(myDiff, myDiffPrev, (myD, myDPrev) => myDPrev !== null && myD !== null && myD < 0 && myDPrev >= 0);

// -----------------------------------------------------------------
// Painting
// -----------------------------------------------------------------
const myLine1Color = for_every(myLine1, myLine2, (myV1, myV2) => myV1 > myV2 ? '#2eba22' : '#d91c1c');
const myLine2Color = for_every(myLine1, myLine2, (myV1, myV2) => myV1 > myV2 ? '#199410' : '#941010');

paint(myLine1, { name: 'Line1', color: myLine1Color, thickness: 2 });
paint(myLine2, { name: 'Line2', color: myLine2Color, thickness: 2 });

const myCrossUpMarks = for_every(myCrossUp, myUp => myUp ? constants.icons.triangle_up : null);
const myCrossDownMarks = for_every(myCrossDown, myDown => myDown ? constants.icons.triangle_down : null);

paint(myCrossUpMarks, { name: 'CrossUp', style: 'labels_below', color: 'green' });
paint(myCrossDownMarks, { name: 'CrossDown', style: 'labels_above', color: 'red' });

// -----------------------------------------------------------------
// Signals for scanner / alerts / strategy tester
// -----------------------------------------------------------------
const myLongEntrySignal = for_every(myCrossUp, myUp => (myDirection === 'both' || myDirection === 'long') && myUp);
const myLongCloseSignal = for_every(myCrossDown, myDown => (myDirection === 'both' || myDirection === 'long') && myDown);
const myShortEntrySignal = for_every(myCrossDown, myDown => (myDirection === 'both' || myDirection === 'short') && myDown);
const myShortCloseSignal = for_every(myCrossUp, myUp => (myDirection === 'both' || myDirection === 'short') && myUp);

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myLongCloseSignal, 'Long Close');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myShortCloseSignal, 'Short Close');