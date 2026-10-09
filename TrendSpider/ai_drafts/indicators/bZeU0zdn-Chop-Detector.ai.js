describe_indicator('Chop Detector', 'lower', { decimals: 3 });

// ── Inputs ──────────────────────────────────────────────────────────────
const myLenTab = input.tab('Smoothing');
const myLen = myLenTab.number('Smoothing lookback', 20, { min: 1, max: 200 });
const myCenter = myLenTab.boolean('Center the plot', true);
const myWeightsRow = myLenTab.row();
const myWCenter = myWeightsRow.number('Center weight', 0.5, { min: 0, max: 5, step: 0.05 });
const myWNear = myWeightsRow.number('Adjacent weight', 0.25, { min: 0, max: 5, step: 0.05 });
const myWFar = myWeightsRow.number('Outer weight', 0.1, { min: 0, max: 5, step: 0.05 });

const myBrkTab = input.tab('Breakout Damping');
const myUseBrk = myBrkTab.boolean('Breakout damping', true);
const myBrkRow1 = myBrkTab.row();
const myW5 = myBrkRow1.number('Weight on last 5 wicks', 0.7, { min: 0, max: 1, step: 0.05 });
const myBrkTrig = myBrkRow1.number('Trigger: body / wick ref', 1.0, { min: 0, max: 10, step: 0.1 });
const myBrkRow2 = myBrkTab.row();
const myBrkStr = myBrkRow2.number('Damping strength', 0.5, { min: 0, max: 5, step: 0.05 });
const myBrkHold = myBrkRow2.number('Hold bars', 4, { min: 1, max: 50 });
const mySmooth = myBrkTab.number('Output smoothing', 2, { min: 1, max: 50 });

const myThrTab = input.tab('Thresholds');
const myThrRow1 = myThrTab.row();
const myLimeThr = myThrRow1.number('Lime below', 0.53, { min: 0, max: 5, step: 0.01 });
const myLoThr = myThrRow1.number('Yellow from', 0.53, { min: 0, max: 5, step: 0.01 });
const myThrRow2 = myThrTab.row();
const myHiThr = myThrRow2.number('Red at', 0.95, { min: 0, max: 5, step: 0.01 });
const myBlackThr = myThrRow2.number('Black above', 1.0, { min: 0, max: 5, step: 0.01 });

// ── Core math (mirrors the Pine script) ───────────────────────────────
const myWick = add(
	sub(high, max_of(open, close)),
	sub(min_of(open, close), low)
);
const myBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));

const myRaw = div(sma(myWick, myLen), sma(myBody, myLen));

// raw[0]..raw[4] in Pine (0 = current bar, 4 = four bars back)
const myRaw0 = myRaw;
const myRaw1 = shift(myRaw, 1);
const myRaw2 = shift(myRaw, 2);
const myRaw3 = shift(myRaw, 3);
const myRaw4 = shift(myRaw, 4);

const myNum = add(
	mult(myRaw2, myWCenter),
	mult(add(myRaw1, myRaw3), myWNear),
	mult(add(myRaw0, myRaw4), myWFar)
);
const myDen = myWCenter + 2 * myWNear + 2 * myWFar;
const myBase = div(myNum, myDen);

const myWickRef = add(
	mult(sma(myWick, 5), myW5),
	mult(sma(myWick, 10), 1 - myW5)
);

const myBrk = for_every(myBody, myWickRef, (_b, _wr) => (_wr > 0 ? _b / _wr : 0));
const myBrkNow = for_every(myBrk, _b => Math.max(_b - myBrkTrig, 0));
const myBrkMax = highest(myBrkNow, myBrkHold);

const myDamp = myUseBrk
	? for_every(myBrkMax, _m => 1 / (1 + myBrkStr * _m))
	: series_of(1);

const myV = sma(mult(myBase, myDamp), mySmooth);

// Pine's negative plot offset shifts the plot visually backwards in time.
// shift(series, -2) reproduces "offset = -2" from the Pine script.
const myCenterOffset = myCenter ? -2 : 0;
const myVShifted = shift(myV, myCenterOffset);

// ── Color gradient (reproduces color.from_gradient) ───────────────────
function myHexToRgb(_hex) {
	const myClean = _hex.replace('#', '');
	return {
		r: parseInt(myClean.substring(0, 2), 16),
		g: parseInt(myClean.substring(2, 4), 16),
		b: parseInt(myClean.substring(4, 6), 16)
	};
}

function myGradientColor(_t, _from, _to, _colorFrom, _colorTo) {
	const myRatio = Math.min(Math.max((_t - _from) / (_to - _from), 0), 1);
	const myC1 = myHexToRgb(_colorFrom);
	const myC2 = myHexToRgb(_colorTo);
	const myR = Math.round(myC1.r + (myC2.r - myC1.r) * myRatio);
	const myG = Math.round(myC1.g + (myC2.g - myC1.g) * myRatio);
	const myB = Math.round(myC1.b + (myC2.b - myC1.b) * myRatio);
	return `rgb(${myR}, ${myG}, ${myB})`;
}

const myT = for_every(myVShifted, _vv => Math.min(Math.max((_vv - myLoThr) / (myHiThr - myLoThr), 0), 1));

const myCol = for_every(myVShifted, myT, (_vv, _tt) => {
	if (_vv === null) return null;
	if (_vv > myBlackThr) return '#000000';
	if (_vv < myLimeThr) return '#97C459';
	if (_tt < 0.5) return myGradientColor(_tt, 0, 0.5, '#1D9E75', '#EF9F27');
	return myGradientColor(_tt, 0.5, 1, '#EF9F27', '#E24B4A');
});

// ── Painting ────────────────────────────────────────────────────────────
paint(myVShifted, { name: 'Chop', style: 'column', color: myCol, thickness: 3 });

paint(horizontal_line(myBlackThr), { name: 'Black Threshold', color: 'rgba(0,0,0,0.4)', style: 'line' });
paint(horizontal_line(myHiThr), { name: 'Red Threshold', color: 'rgba(226,75,74,0.4)', style: 'line' });
paint(horizontal_line(myLoThr), { name: 'Yellow Threshold', color: 'rgba(29,158,117,0.4)', style: 'line' });
paint(horizontal_line(myLimeThr), { name: 'Lime Threshold', color: 'rgba(151,196,89,0.4)', style: 'line' });

// ── Signals for scanner/strategy/alerts ──────────────────────────────────
// Signals are computed on the unshifted value (myV) to avoid using
// forward-looking data, since the visual plot offset is purely cosmetic.
const mySignalLime = for_every(myV, _vv => _vv < myLimeThr);
const mySignalYellow = for_every(myV, _vv => _vv >= myLoThr && _vv < myHiThr);
const mySignalRed = for_every(myV, _vv => _vv >= myHiThr && _vv <= myBlackThr);
const mySignalBlack = for_every(myV, _vv => _vv > myBlackThr);

register_signal(mySignalLime, 'Lime Zone (Low Chop)');
register_signal(mySignalYellow, 'Yellow Zone (Transition)');
register_signal(mySignalRed, 'Red Zone (High Chop)');
register_signal(mySignalBlack, 'Black Zone (Extreme Chop)');