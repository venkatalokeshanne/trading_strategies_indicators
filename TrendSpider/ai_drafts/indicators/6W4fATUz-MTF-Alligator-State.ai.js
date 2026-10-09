describe_indicator('MTF Alligator State', 'overlay');

// ============================================================
// INPUTS
// ============================================================
const myAlligatorTab = input.tab('Alligator');
const mySourceSelect = myAlligatorTab.select('Source', 'hl2', constants.price_source_options);
const myJawLen = myAlligatorTab.number('Jaw Length', 13, { min: 1, max: 200 });
const myJawOff = myAlligatorTab.number('Jaw Offset', 8, { min: 0, max: 50 });
const myTeethLen = myAlligatorTab.number('Teeth Length', 8, { min: 1, max: 200 });
const myTeethOff = myAlligatorTab.number('Teeth Offset', 5, { min: 0, max: 50 });
const myLipsLen = myAlligatorTab.number('Lips Length', 5, { min: 1, max: 200 });
const myLipsOff = myAlligatorTab.number('Lips Offset', 3, { min: 0, max: 50 });

const myDisplayTab = input.tab('Display');
const myConfirmedOnly = myDisplayTab.boolean('Use closed HTF bars only', true);
const myTablePosition = myDisplayTab.select('Table position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);

const mySource = market[mySourceSelect];

// ============================================================
// Computes the state series (1 = BUY, -1 = SELL, 0 = SIDEWAYS)
// for a given set of ohlc data (works both for current chart
// data and for data fetched via request.history)
// ============================================================
function myComputeState(_srcSeries, _closeSeries) {
	const myJaw = shift(wildma(_srcSeries, myJawLen), myJawOff);
	const myTeeth = shift(wildma(_srcSeries, myTeethLen), myTeethOff);
	const myLips = shift(wildma(_srcSeries, myLipsLen), myLipsOff);

	const myState = for_every(myLips, myTeeth, myJaw, _closeSeries, (_lips, _teeth, _jaw, _close) => {
		const myIsBuy = _lips > _teeth && _teeth > _jaw && _close > _lips;
		const myIsSell = _lips < _teeth && _teeth < _jaw && _close < _lips;
		return myIsBuy ? 1 : (myIsSell ? -1 : 0);
	});

	// Pine's "confirmedOnly" uses the previous bar's value (st[1])
	return myConfirmedOnly ? shift(myState, 1) : myState;
}

// ============================================================
// Fetches higher/other time frame data and lands the computed
// state onto the current chart's time series. We use "ge" for
// landing and "constant" for interpolation to keep this
// non-repainting and backtest safe.
// ============================================================
async function myStateOnCurrentChart(_resolution) {
	const myData = await request.history(current.ticker, _resolution);
	assert(!myData.error, `Error fetching ${_resolution} data: "${myData.error}"`);

	const mySrcHTF = _resolution === 'D' ? myData.close : myData.close; // placeholder, replaced below
	// Build the chosen price source on the fetched time frame
	const myHTFSourceSeries = (() => {
		switch (mySourceSelect) {
			case 'open': return myData.open;
			case 'high': return myData.high;
			case 'low': return myData.low;
			case 'hl2': return div(add(myData.high, myData.low), 2);
			case 'oc2': return div(add(myData.open, myData.close), 2);
			case 'hlc3': return div(add(add(myData.high, myData.low), myData.close), 3);
			case 'ohlc4': return div(add(add(add(myData.open, myData.high), myData.low), myData.close), 4);
			default: return myData.close;
		}
	})();

	const myHTFState = myComputeState(myHTFSourceSeries, myData.close);
	const myLanded = land_points_onto_series(myData.time, myHTFState, time, 'ge');
	return interpolate_sparse_series(myLanded, 'constant');
}

const [myStateW1, myStateD1, myStateH4, myStateH1] = await Promise.all([
	myStateOnCurrentChart('W'),
	myStateOnCurrentChart('D'),
	myStateOnCurrentChart('240'),
	myStateOnCurrentChart('60')
]);

// ============================================================
// Labels, colors, and overlay table (static UI replica of the
// Pine Script table.new output)
// ============================================================
function myLabelFor(_state) {
	return _state === 1 ? 'BUY' : (_state === -1 ? 'SELL' : 'SIDEWAYS');
}

function myColorFor(_state) {
	return _state === 1 ? '#1b9e4b' : (_state === -1 ? '#d1392b' : '#808080');
}

const myLastW1 = myStateW1[myStateW1.length - 1];
const myLastD1 = myStateD1[myStateD1.length - 1];
const myLastH4 = myStateH4[myStateH4.length - 1];
const myLastH1 = myStateH1[myStateH1.length - 1];

paint_overlay('AlligatorMTFTable', { position: myTablePosition }, {
	rows: [{
		cells: [
			{ text: 'TF', color: '#ffffff', background_color: '#000000' },
			{ text: 'STATE', color: '#ffffff', background_color: '#000000' }
		]
	}, {
		cells: [
			{ text: 'W1', color: '#ffffff', background_color: '#333333' },
			{ text: myLabelFor(myLastW1), color: '#ffffff', background_color: myColorFor(myLastW1) }
		]
	}, {
		cells: [
			{ text: 'D1', color: '#ffffff', background_color: '#333333' },
			{ text: myLabelFor(myLastD1), color: '#ffffff', background_color: myColorFor(myLastD1) }
		]
	}, {
		cells: [
			{ text: 'H4', color: '#ffffff', background_color: '#333333' },
			{ text: myLabelFor(myLastH4), color: '#ffffff', background_color: myColorFor(myLastH4) }
		]
	}, {
		cells: [
			{ text: 'H1', color: '#ffffff', background_color: '#333333' },
			{ text: myLabelFor(myLastH1), color: '#ffffff', background_color: myColorFor(myLastH1) }
		]
	}]
});

// ============================================================
// Signals for scanning, alerts, and strategy testing
// ============================================================
register_signal(for_every(myStateW1, _s => _s === 1), 'W1 Buy');
register_signal(for_every(myStateW1, _s => _s === -1), 'W1 Sell');
register_signal(for_every(myStateD1, _s => _s === 1), 'D1 Buy');
register_signal(for_every(myStateD1, _s => _s === -1), 'D1 Sell');
register_signal(for_every(myStateH4, _s => _s === 1), 'H4 Buy');
register_signal(for_every(myStateH4, _s => _s === -1), 'H4 Sell');
register_signal(for_every(myStateH1, _s => _s === 1), 'H1 Buy');
register_signal(for_every(myStateH1, _s => _s === -1), 'H1 Sell');

const myAllBuy = for_every(myStateW1, myStateD1, myStateH4, myStateH1, (_w, _d, _h4, _h1) => _w === 1 && _d === 1 && _h4 === 1 && _h1 === 1);
const myAllSell = for_every(myStateW1, myStateD1, myStateH4, myStateH1, (_w, _d, _h4, _h1) => _w === -1 && _d === -1 && _h4 === -1 && _h1 === -1);

register_signal(myAllBuy, 'All Timeframes Buy');
register_signal(myAllSell, 'All Timeframes Sell');