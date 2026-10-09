describe_indicator('Box Breakout Strategy', 'price');

// Inputs organized in tabs/groups since we have more than 4 parameters
const boxTab = input.tab('Box Settings');
const myBoxLength = boxTab.number('Box Length', 20, { min: 5, max: 500 });
const myAtrLength = boxTab.number('ATR Length', 14, { min: 1, max: 200 });

const riskTab = input.tab('Risk Settings');
const myAtrMultiplier = riskTab.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myRiskReward = riskTab.number('Risk Reward', 2.0, { min: 0.1, max: 20, step: 0.1 });

const volTab = input.tab('Volume Settings');
const myUseVolume = volTab.boolean('Use Volume Confirmation', true);
const myVolumeLength = volTab.number('Volume MA Length', 20, { min: 1, max: 500 });

// Box high/low are computed off PRIOR candle's high/low (Pine's high[1], low[1])
// so no look-ahead bias is introduced.
const myShiftedHigh = shift(high, 1);
const myShiftedLow = shift(low, 1);

const myBoxHigh = highest(myShiftedHigh, myBoxLength);
const myBoxLow = lowest(myShiftedLow, myBoxLength);
const myBoxMid = div(add(myBoxHigh, myBoxLow), 2);

const myAtr = atr(high, low, close, myAtrLength);
const myAvgVolume = sma(volume, myVolumeLength);

const myVolumeConfirm = for_every(volume, myAvgVolume, (_v, _av) => _v > _av);

const myBullBreakout = for_every(close, myBoxHigh, myVolumeConfirm, (_c, _bh, _vc) => _c > _bh && (!myUseVolume || _vc));
const myBearBreakout = for_every(close, myBoxLow, myVolumeConfirm, (_c, _bl, _vc) => _c < _bl && (!myUseVolume || _vc));

// Stop/target calculations (for reference, matching Pine formulas exactly)
const myLongStop = sub(close, mult(myAtr, myAtrMultiplier));
const myLongTarget = add(close, mult(sub(close, myLongStop), myRiskReward));

const myShortStop = add(close, mult(myAtr, myAtrMultiplier));
const myShortTarget = sub(close, mult(sub(myShortStop, close), myRiskReward));

// Box levels
paint(myBoxHigh, { name: 'BoxHigh', color: '#26A69A', thickness: 2 });
paint(myBoxLow, { name: 'BoxLow', color: '#EF5350', thickness: 2 });
paint(myBoxMid, { name: 'BoxMid', color: 'gray', style: 'dotted' });

// Signal markers (labels above/below candles, as in Pine plotshape)
const myBuyMarks = for_every(myBullBreakout, _b => _b ? constants.icons.arrow_up : null);
const mySellMarks = for_every(myBearBreakout, _s => _s ? constants.icons.arrow_down : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: 'red' });

// Background highlight equivalent (color.new(green,88) / color.new(red,88) / na)
const myBgColors = for_every(close, myBoxHigh, myBoxLow, (_c, _bh, _bl) => {
	if (_c > _bh) return 'rgba(0,128,0,0.12)';
	if (_c < _bl) return 'rgba(255,0,0,0.12)';
	return null;
});
color_candles(myBgColors);

// Signals for scanners, alerts, strategy tester
register_signal(myBullBreakout, 'Bull Breakout');
register_signal(myBearBreakout, 'Bear Breakout');