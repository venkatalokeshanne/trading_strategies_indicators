describe_indicator('Mask Man 9 and Price Movement V2', 'price');

// Inputs mirroring the Pine script
const myLength = input.number('Mask Man Length', 9, { min: 1, max: 200 });
const myPmLength = input.number('Price Movement Lookback', 5, { min: 1, max: 200 });
const myShowSignals = input.boolean('Show Buy Sell Signals', true);

// Source is hlc3, as in the Pine script (ta.ema(hlc3, length))
const mySource = hlc3;

// Mask Man EMA
const myMaskMa = ema(mySource, myLength);

// Price change over pmLength bars (ta.change(src, len) = src - src[len])
const myPriceChange = sub(mySource, shift(mySource, myPmLength));
const myPmBull = for_every(myPriceChange, _c => _c > 0);
const myPmBear = for_every(myPriceChange, _c => _c < 0);

// Crossover / crossunder of source vs maskMa
const myCrossUp = for_every(mySource, myMaskMa, (_s, _m, _prev, _i) => {
	if (_i === 0) return false;
	return _s > _m && mySource[_i - 1] <= myMaskMa[_i - 1];
});

const myCrossDown = for_every(mySource, myMaskMa, (_s, _m, _prev, _i) => {
	if (_i === 0) return false;
	return _s < _m && mySource[_i - 1] >= myMaskMa[_i - 1];
});

// Buy/Sell trigger conditions
const myBuyCond = for_every(myCrossUp, myPmBull, (_cu, _bull) => _cu && _bull);
const mySellCond = for_every(myCrossDown, myPmBear, (_cd, _bear) => _cd && _bear);

// Visual markers (null when conditions are false or signals hidden)
const myBuyMarks = for_every(myBuyCond, low, (_b, _l) => (myShowSignals && _b) ? _l : null);
const mySellMarks = for_every(mySellCond, high, (_s, _h) => (myShowSignals && _s) ? _h : null);

paint(myMaskMa, { name: 'MaskManEMA', color: '#2962FF', thickness: 2 });
paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350' });

// Signals for scanners, alerts and strategy tester
register_signal(myBuyCond, 'Mask Man Buy Signal');
register_signal(mySellCond, 'Mask Man Sell Signal');