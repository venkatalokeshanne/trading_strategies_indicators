describe_indicator('Up Dn Volume Sentiment R', 'lower');

// ═══════════════════════════════════════════════════════════════
// INPUTS
// ═══════════════════════════════════════════════════════════════
const myMaLength = input.number('Up/Dn Vol Length', 50, { min: 1, max: 1000 });
const myNormLookback = input.number('Normalization Lookback', 756, { min: 50, max: 5000 });

const myLevelsRow = input.row();
// shortened titles to satisfy the platform's input name length limit
const myLongLevel = myLevelsRow.number('Long Entry Level', 10, { min: 0, max: 100 });
const myShortLevel = myLevelsRow.number('Short Entry Level', 90, { min: 0, max: 100 });

const myRiskRow = input.row();
const myStopPercent = myRiskRow.number('Stop Loss Percent', 5.0, { min: 0.01, max: 100 });
const myRTarget = myRiskRow.number('Profit Target R', 2.0, { min: 0.01, max: 100 });

// ═══════════════════════════════════════════════════════════════
// UP / DOWN VOLUME
// ═══════════════════════════════════════════════════════════════
// upVol = volume on up candles, dnVol = volume on down candles
const myCloseShift1 = shift(close, 1);
const myUpVol = for_every(close, myCloseShift1, volume, (_c, _cp, _v) => _c > _cp ? _v : 0);
const myDnVol = for_every(close, myCloseShift1, volume, (_c, _cp, _v) => _c < _cp ? _v : 0);

const mySumUp = sma(myUpVol, myMaLength);
const mySumDn = sma(myDnVol, myMaLength);

// Pine: na when sumDn == 0, here we use null for the same purpose
const myUpDnVolRatio = for_every(mySumUp, mySumDn, (_up, _dn) => _dn === 0 ? null : _up / _dn);

// ═══════════════════════════════════════════════════════════════
// NORMALIZATION
// ═══════════════════════════════════════════════════════════════
// highest()/lowest() in this engine ignore nulls in the same trailing
// window fashion as Pine Script's ta.highest/ta.lowest treat na values
const myLowestRatio = lowest(myUpDnVolRatio, myNormLookback);
const myHighestRatio = highest(myUpDnVolRatio, myNormLookback);

const mySentimentOsc = for_every(
	myUpDnVolRatio,
	myLowestRatio,
	myHighestRatio,
	(_ratio, _lo, _hi) => {
		if (_ratio === null || _lo === null || _hi === null || _hi === _lo) {
			return null;
		}
		return (_ratio - _lo) / (_hi - _lo) * 100;
	}
);

// ═══════════════════════════════════════════════════════════════
// ENTRY CONDITIONS
// ═══════════════════════════════════════════════════════════════
const myLongCondition = for_every(mySentimentOsc, _osc => _osc !== null && _osc <= myLongLevel);
const myShortCondition = for_every(mySentimentOsc, _osc => _osc !== null && _osc >= myShortLevel);

register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// ═══════════════════════════════════════════════════════════════
// PLOTS
// ═══════════════════════════════════════════════════════════════
paint(mySentimentOsc, { name: 'Sentiment Oscillator', color: '#FF9800', style: 'line' });
paint(horizontal_line(myLongLevel), { name: 'Long Entry Level', color: '#26A69A', style: 'dotted' });
paint(horizontal_line(myShortLevel), { name: 'Short Entry Level', color: '#EF5350', style: 'dotted' });
paint(horizontal_line(50), { name: 'Neutral Level', color: 'gray', style: 'dotted' });