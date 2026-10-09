describe_indicator('RSI plus Williams Vix Fix', 'lower');

// ===================== RSI inputs =====================
const myRsiTab = input.tab('RSI');
const myRsiLength = myRsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiSource = myRsiTab.select('RSI Source', 'close', constants.price_source_options);
const myOverbought = myRsiTab.number('Overbought', 70, { min: 1, max: 100 });
const myOversold = myRsiTab.number('Oversold', 30, { min: 0, max: 99 });

// ===================== WVF inputs =====================
const myWvfTab = input.tab('Williams Vix Fix');
const myPd = myWvfTab.number('StDev Lookback', 22, { min: 1, max: 500 });
const myBbl = myWvfTab.number('BB Length', 20, { min: 1, max: 500 });
const myMult = myWvfTab.number('BB StDev Mult', 2, { min: 1, max: 5 });
const myLb = myWvfTab.number('Percentile Lookback', 50, { min: 1, max: 500 });
const myPh = myWvfTab.number('Highest Percentile', 0.85, { min: 0, max: 5 });
const myPl = myWvfTab.number('Lowest Percentile', 1.01, { min: 0, max: 5 });
const myShowPercentileLines = myWvfTab.boolean('Show Percentile Lines', false);
const myShowStdevLine = myWvfTab.boolean('Show StDev Line', false);
const myZoneRow = myWvfTab.row();
const myZoneBottom = myZoneRow.number('WVF Zone Bottom', 40, { min: 0, max: 100 });
const myZoneTop = myZoneRow.number('WVF Zone Top', 60, { min: 0, max: 100 });
const myNormRow = myWvfTab.row();
const myDynNormalize = myNormRow.boolean('Auto Normalize WVF', true);
const myDynLookback = myNormRow.number('Normalize Lookback', 100, { min: 10, max: 1000 });

// ===================== Price source =====================
const myPrice = market[myRsiSource];

// ===================== RSI calculation =====================
const myRsiValue = rsi(myPrice, myRsiLength);

// ===================== WVF calculation =====================
const myHighestClose = highest(close, myPd);
const myWvf = mult(div(sub(myHighestClose, low), myHighestClose), 100);
const myMidLine = sma(myWvf, myBbl);
const mySDev = mult(stdev(myWvf, myBbl), myMult);
const myUpperBand = add(myMidLine, mySDev);
const myRangeHigh = mult(highest(myWvf, myLb), myPh);
const myRangeLow = mult(lowest(myWvf, myLb), myPl);

// column coloring: lime if wvf >= upperBand OR wvf >= rangeHigh, else gray
const myColColor = for_every(myWvf, myUpperBand, myRangeHigh, (_wvf, _upper, _rangeHigh) => (
	(_wvf >= _upper || _wvf >= _rangeHigh) ? '#00FF00' : '#808080'
));

// signal series for scanning: true when the column is "lime" (triggered)
const myWvfSignal = for_every(myWvf, myUpperBand, myRangeHigh, (_wvf, _upper, _rangeHigh) => (
	_wvf >= _upper || _wvf >= _rangeHigh
));

// normalization
const myWvfMin = lowest(myWvf, myDynLookback);
const myWvfMax = highest(myWvf, myDynLookback);
const myWvfNorm = myDynNormalize
	? for_every(myWvf, myWvfMin, myWvfMax, (_wvf, _min, _max) => (
		_max > _min ? ((_wvf - _min) / (_max - _min)) * 100 : 0
	))
	: myWvf;

// mapToZone(val) = zoneBottom + val * scale
const myZoneScale = (myZoneTop - myZoneBottom) / 100.0;
const mapToZone = _series => for_every(_series, _v => myZoneBottom + _v * myZoneScale);
const myMappedWvf = mapToZone(myWvfNorm);
const myMappedRangeHigh = myShowPercentileLines ? mapToZone(myRangeHigh) : constants.empty_series;
const myMappedRangeLow = myShowPercentileLines ? mapToZone(myRangeLow) : constants.empty_series;
const myMappedUpperBand = myShowStdevLine ? mapToZone(myUpperBand) : constants.empty_series;

// ===================== Painting =====================
paint(myRsiValue, { name: 'RSI', color: '#2962FF', thickness: 2, style: 'line' });
paint(horizontal_line(myOverbought), { name: 'Overbought', color: '#787B86', style: 'dotted' });
paint(horizontal_line(50), { name: 'Middle', color: '#787B86', style: 'dotted' });
paint(horizontal_line(myOversold), { name: 'Oversold', color: '#787B86', style: 'dotted' });
paint(myMappedRangeHigh, { name: 'Range High Percentile', color: 'orange', thickness: 2, style: 'line' });
paint(myMappedRangeLow, { name: 'Range Low Percentile', color: 'orange', thickness: 2, style: 'line' });
paint(myMappedWvf, { name: 'Williams Vix Fix', color: myColColor, thickness: 4, style: 'column' });
paint(myMappedUpperBand, { name: 'Upper Band StdDev', color: 'aqua', thickness: 2, style: 'line' });

// ===================== Signals for scanners, alerts, strategies =====================
const myRsiOverboughtSignal = for_every(myRsiValue, _r => _r >= myOverbought);
const myRsiOversoldSignal = for_every(myRsiValue, _r => _r <= myOversold);
register_signal(myRsiOverboughtSignal, 'RSI Overbought');
register_signal(myRsiOversoldSignal, 'RSI Oversold');
register_signal(myWvfSignal, 'Williams Vix Fix Triggered');