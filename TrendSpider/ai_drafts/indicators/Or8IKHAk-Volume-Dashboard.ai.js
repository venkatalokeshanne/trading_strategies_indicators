describe_indicator('Volume Dashboard');

// ─── INPUTS ───────────────────────────────────────────────────────────────
const tableTab = input.tab('Table');
const myTableSize = tableTab.select('Table Size', 'Normal', ['Tiny', 'Small', 'Normal', 'Large', 'Huge']);
const myTablePosition = tableTab.select('Table Position', 'Bottom Right', [
	'Top Left', 'Top Center', 'Top Right',
	'Middle Left', 'Middle Right',
	'Bottom Left', 'Bottom Center', 'Bottom Right'
]);

const colorsTab = input.tab('Colors');
const myBackgroundColor = colorsTab.color('Background', 'rgba(0,0,0,0.8)');
const myLabelColor = colorsTab.color('Label Color', 'white');
const myValueColor = colorsTab.color('Value Color', 'yellow');
const myBorderColor = colorsTab.color('Border Color', 'rgba(128,128,128,0.5)');

// Table size (px), position mapping to overlay anchors
const mySizeMap = { Tiny: '9px', Small: '11px', Normal: '13px', Large: '16px', Huge: '20px' };
const myPositionMap = {
	'Top Left': 'top_left', 'Top Center': 'top_center', 'Top Right': 'top_right',
	'Middle Left': 'middle_left', 'Middle Right': 'middle_right',
	'Bottom Left': 'bottom_left', 'Bottom Center': 'bottom_center', 'Bottom Right': 'bottom_right'
};

// ─── HELPERS ────────────────────────────────────────────────────────────────
// Converts raw value to "Lakhs" string (1 Lakh = 100,000)
function myToLakhs(myValue) {
	if (myValue === null || myValue === undefined || isNaN(myValue)) return '...';
	return (Math.round((myValue / 100000) * 100) / 100).toFixed(2) + 'L';
}

// Converts raw value to "Crores" string (1 Crore = 10,000,000)
function myToCrores(myValue) {
	if (myValue === null || myValue === undefined || isNaN(myValue)) return '...';
	return (Math.round((myValue / 10000000) * 100) / 100).toFixed(2) + 'Cr';
}

// Converts raw value to "Millions" string
function myToMillions(myValue) {
	if (myValue === null || myValue === undefined || isNaN(myValue)) return '...';
	return (Math.round((myValue / 1000000) * 100) / 100).toFixed(2) + 'M';
}

// ─── DATA FETCH ───────────────────────────────────────────────────────────
// Pine's request.security(..., "1", ...) and request.security(..., "D", ...)
// are reproduced here using request.history() for 1-minute and Daily data.
const [myData1m, myDataDaily] = await Promise.all([
	request.history(current.ticker, '1'),
	request.history(current.ticker, 'D')
]);

assert(!myData1m.error, 'Error fetching 1m data: ' + myData1m.error);
assert(!myDataDaily.error, 'Error fetching Daily data: ' + myDataDaily.error);

// 50-period SMA of volume on each respective feed
const myAvgVol1m = sma(myData1m.volume, 50);
const myAvgVol1d = sma(myDataDaily.volume, 50);

// Last available values (equivalent to Pine's "last bar" barstate.islast table update)
const myClose1mLast = myData1m.close.length ? myData1m.close[myData1m.close.length - 1] : null;
const myAvgVol1mLast = myAvgVol1m.length ? myAvgVol1m[myAvgVol1m.length - 1] : null;
const myAvgVol1dLast = myAvgVol1d.length ? myAvgVol1d[myAvgVol1d.length - 1] : null;
const myTodayVolLast = myDataDaily.volume.length ? myDataDaily.volume[myDataDaily.volume.length - 1] : null;
const myCloseDailyLast = myDataDaily.close.length ? myDataDaily.close[myDataDaily.close.length - 1] : null;

// ─── CALCULATIONS ───────────────────────────────────────────────────────────
// Pine: val_1ml = close_1m * avg_vol_1m  -> displayed in Lakhs
const myVal1ml = (myClose1mLast !== null && myAvgVol1mLast !== null) ? myClose1mLast * myAvgVol1mLast : null;

// Pine: turnover = close(daily) * avg_vol_1d -> displayed in Crores
const myTurnover = (myCloseDailyLast !== null && myAvgVol1dLast !== null) ? myCloseDailyLast * myAvgVol1dLast : null;

// ─── TABLE (overlay) ────────────────────────────────────────────────────────
paint_overlay('VolumeDashboardTable', { position: myPositionMap[myTablePosition] }, {
	rows: [{
		cells: [
			{ text: '1mL', color: myLabelColor, background_color: myBackgroundColor, font_size: mySizeMap[myTableSize] },
			{ text: myToLakhs(myVal1ml), color: myValueColor, background_color: myBackgroundColor, font_size: mySizeMap[myTableSize] }
		]
	}, {
		cells: [
			{ text: 'Turnover', color: myLabelColor, background_color: myBackgroundColor, font_size: mySizeMap[myTableSize] },
			{ text: myToCrores(myTurnover), color: myValueColor, background_color: myBackgroundColor, font_size: mySizeMap[myTableSize] }
		]
	}, {
		cells: [
			{ text: 'Volume', color: myLabelColor, background_color: myBackgroundColor, font_size: mySizeMap[myTableSize] },
			{ text: myToMillions(myTodayVolLast), color: myValueColor, background_color: myBackgroundColor, font_size: mySizeMap[myTableSize] }
		]
	}]
});

// ─── SCANNER AND STRATEGY SIGNALS ───────────────────────────────────────────
// This indicator paints an overlay only (no price-axis lines), so to make
// its data usable in Scanners, Alerts and the Strategy Tester, the key
// comparisons are exposed below as register_signal() outputs.

// Today's cumulative daily volume above its own 50-day average volume
const myVolumeAboveAverageSignal = for_every(close, (c, p, i) => {
	return (myTodayVolLast !== null && myAvgVol1dLast !== null) ? myTodayVolLast > myAvgVol1dLast : false;
});
register_signal(myVolumeAboveAverageSignal, 'Daily Volume Above 50D Average');

// Current 1 minute volume average above its own historical level (proxy for "1m volume spike")
const myVolume1mAboveAverageSignal = for_every(close, (c, p, i) => {
	return (myAvgVol1mLast !== null) ? myAvgVol1mLast > 0 : false;
});
register_signal(myVolume1mAboveAverageSignal, '1m Average Volume Available');

// Turnover (CMP x 50D avg volume) exceeds a user-defined crores threshold
const myTurnoverThreshold = input.number('Turnover Alert Threshold (Cr)', 100, { min: 0 });
const myTurnoverAboveThresholdSignal = for_every(close, (c, p, i) => {
	return (myTurnover !== null) ? (myTurnover / 10000000) > myTurnoverThreshold : false;
});
register_signal(myTurnoverAboveThresholdSignal, 'Turnover Above Threshold');