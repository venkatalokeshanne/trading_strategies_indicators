describe_indicator('Whale Absorption and Liquidity Zones', 'price');

// --- INPUTS ---
const myVolMaLength = input.number('Volume MA Length', 20, { min: 1, max: 500 });
const myVolMultiplier = input.number('Whale Volume Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myLookbackLiquidity = input.number('Liquidity Pivot Lookback', 20, { min: 5, max: 200 });

// --- VOLUME / WHALE LOGIC ---
const myAvgVol = sma(volume, myVolMaLength);
const myIsHighVol = for_every(volume, myAvgVol, (_v, _avg) => _v > _avg * myVolMultiplier);

// Buy absorption: high volume + close near the high + close above open
const myIsBuyAbsorption = for_every(myIsHighVol, close, open, high, low, (_hv, _c, _o, _h, _l) => {
	return _hv && _c > (_l + (_h - _l) * 0.6) && _c > _o;
});

// Sell absorption: high volume + close near the low + close below open
const myIsSellAbsorption = for_every(myIsHighVol, close, open, high, low, (_hv, _c, _o, _h, _l) => {
	return _hv && _c < (_l + (_h - _l) * 0.4) && _c < _o;
});

// --- CANDLE COLORING ---
const myBarColors = for_every(myIsBuyAbsorption, myIsSellAbsorption, (_buy, _sell) => {
	if (_buy) return '#00ff08';
	if (_sell) return '#ff0055';
	return null;
});
color_candles(myBarColors);

// --- SIGNAL SHAPES (triangle markers below/above bar) ---
const myBuyMarkers = for_every(myIsBuyAbsorption, _buy => _buy ? constants.icons.triangle_up : null);
const mySellMarkers = for_every(myIsSellAbsorption, _sell => _sell ? constants.icons.triangle_down : null);

paint(myBuyMarkers, { style: 'labels_below', color: 'green', name: 'WhaleBuy' });
paint(mySellMarkers, { style: 'labels_above', color: 'red', name: 'WhaleSell' });

// --- LIQUIDITY PIVOTS ---
// Pine's ta.pivothigh/pivotlow(series, leftbars, rightbars) maps directly
// to pivot_high/pivot_low(series, leftLength, rightLength)
const myPivotHigh = pivot_high(high, myLookbackLiquidity, 5);
const myPivotLow = pivot_low(low, myLookbackLiquidity, 5);

// Zones are extended to the right using constant interpolation (closest
// equivalent to Pine's extend.right lines drawn from each pivot point)
const mySellZone = interpolate_sparse_series(myPivotHigh, 'constant');
const myBuyZone = interpolate_sparse_series(myPivotLow, 'constant');

const mySellZonePainted = paint(mySellZone, { style: 'dotted', color: 'red', name: 'LiquiditySellStops' });
const myBuyZonePainted = paint(myBuyZone, { style: 'dotted', color: 'green', name: 'LiquidityBuyStops' });

// Label every pivot point found (not restricted by the paint() loop rule,
// since paint_label_at_line is not a paint() call)
indexed_points_of(myPivotHigh).forEach(_point => {
	paint_label_at_line(mySellZonePainted, _point.candleIndex, 'LIQUIDEZ SELL STOPS', {
		color: 'white',
		background_color: 'red',
		vertical_align: 'bottom'
	});
});

indexed_points_of(myPivotLow).forEach(_point => {
	paint_label_at_line(myBuyZonePainted, _point.candleIndex, 'LIQUIDEZ BUY STOPS', {
		color: 'white',
		background_color: 'green',
		vertical_align: 'top'
	});
});

// --- SCANNER / ALERT / STRATEGY SIGNALS ---
register_signal(myIsBuyAbsorption, 'Whale Buy Absorption');
register_signal(myIsSellAbsorption, 'Whale Sell Absorption');
register_signal(myIsHighVol, 'High Volume');

// --- DASHBOARD OVERLAY ---
const myVolStatusText = myIsHighVol[myIsHighVol.length - 1] ? 'HIGH' : 'NORMAL';
const myVolStatusColor = myIsHighVol[myIsHighVol.length - 1] ? 'red' : 'green';
const myWhalePresence = (myIsBuyAbsorption[myIsBuyAbsorption.length - 1] || myIsSellAbsorption[myIsSellAbsorption.length - 1]) ? 'DETECTED' : 'NONE';
const myWhaleColor = (myIsBuyAbsorption[myIsBuyAbsorption.length - 1] || myIsSellAbsorption[myIsSellAbsorption.length - 1]) ? 'orange' : 'gray';

paint_overlay('WhaleDashboard', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'Volume Status:', color: 'white' },
			{ text: myVolStatusText, color: 'white', background_color: myVolStatusColor }
		]
	}, {
		cells: [
			{ text: 'Whale Presence:', color: 'white' },
			{ text: myWhalePresence, color: 'white', background_color: myWhaleColor }
		]
	}]
});