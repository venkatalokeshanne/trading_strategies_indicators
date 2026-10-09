describe_indicator('VSA No Supply No Demand', 'price');

const myNsndCount = input.number('NSND Count', 10, { min: 1, max: 100 });
// Pine's syminfo.mintick is approximated using the symbol's decimals,
// since mintick itself is not exposed by the Custom JS API.
const myPip = Math.pow(10, -current.decimals);
const myNoDemand = series_of(null);
const myNoSupply = series_of(null);
const myBullOrBear = series_of('');

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (open[myIndex] > close[myIndex]) {
		myBullOrBear[myIndex] = 'Bear';
	}
	else if (close[myIndex] > open[myIndex]) {
		myBullOrBear[myIndex] = 'Bull';
	}
	else {
		myBullOrBear[myIndex] = '';
	}
}

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// Low volume: current volume lower than previous 2 bars' volume
	const myLowVolume = myIndex >= 2 ?
		(volume[myIndex] < volume[myIndex - 1] && volume[myIndex] < volume[myIndex - 2]) :
		false;

	const myDirection = myBullOrBear[myIndex];
	let myPins = false;

	if (myDirection === 'Bear') {
		myPins = high[myIndex] > open[myIndex] + myPip && low[myIndex] < close[myIndex] - myPip;
	}
	else if (myDirection === 'Bull') {
		myPins = high[myIndex] > close[myIndex] + myPip && low[myIndex] < open[myIndex] - myPip;
	}

	let myBearCloseBelow = false;
	let myBearCloseAbove = false;
	let myBullCloseAbove = false;
	let myBullCloseBelow = false;

	if (myIndex >= myNsndCount) {
		for (let myOffset = 0; myOffset < myNsndCount; myOffset += 1) {
			const myLookbackIndex = myIndex - myOffset;
			const myCloseValue = close[myLookbackIndex];

			if (myDirection === 'Bear') {
				if (myCloseValue < low[myIndex]) {
					myBearCloseBelow = true;
				}
				if (myCloseValue > high[myIndex]) {
					myBearCloseAbove = true;
				}
			}
			if (myDirection === 'Bull') {
				if (myCloseValue > high[myIndex]) {
					myBullCloseAbove = true;
				}
				if (myCloseValue < low[myIndex]) {
					myBullCloseBelow = true;
				}
			}
		}
	}

	const myNoDemandValue = myDirection === 'Bull' && myLowVolume && myPins && !myBullCloseAbove && myBullCloseBelow;
	const myNoSupplyValue = myDirection === 'Bear' && myLowVolume && myPins && !myBearCloseBelow && myBearCloseAbove;

	myNoDemand[myIndex] = myNoDemandValue ? high[myIndex] : null;
	myNoSupply[myIndex] = myNoSupplyValue ? low[myIndex] : null;
}

// paint_label_at_line() does not support labels_above/labels_below
// styled lines, so the ND/NS labels are now provided directly by
// painting these series with the labels_above/labels_below style,
// which already renders text markers on the chart.
paint(myNoDemand, {
	name: 'NoDemand',
	style: 'labels_above',
	color: 'red'
});

paint(myNoSupply, {
	name: 'NoSupply',
	style: 'labels_below',
	color: 'lime'
});

register_signal(for_every(myNoDemand, _nd => _nd !== null), 'No Demand');
register_signal(for_every(myNoSupply, _ns => _ns !== null), 'No Supply');