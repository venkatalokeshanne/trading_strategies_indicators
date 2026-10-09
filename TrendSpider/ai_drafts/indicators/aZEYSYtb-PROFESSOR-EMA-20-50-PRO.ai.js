describe_indicator('EMA 20/50 PRO', 'price');

// ---------------- INPUTS ----------------
const myEmaTab = input.tab('EMA Settings');
const myFastLen = myEmaTab.number('Fast EMA Length', 20, { min: 1, max: 500 });
const mySlowLen = myEmaTab.number('Slow EMA Length', 50, { min: 1, max: 500 });
const mySourceName = myEmaTab.select('Source', 'close', constants.price_source_options);

const myFillTab = input.tab('Trend Fill');
const myShowFill = myFillTab.boolean('Show Trend Fill (Between EMAs)', true);

// ---------------- CALCULATIONS ----------------
const mySource = market[mySourceName];
const myEmaFast = ema(mySource, myFastLen);
const myEmaSlow = ema(mySource, mySlowLen);

// ---------------- PLOTS ----------------
paint(myEmaFast, { name: 'EmaFast', color: '#00E676', thickness: 2 });
paint(myEmaSlow, { name: 'EmaSlow', color: '#FF3D3D', thickness: 2 });

// Trend fill between the EMAs, colored dynamically by trend direction.
// If "Show Trend Fill" is off, we simply paint fully transparent (null) fill
// by passing opacity 0, since color_cloud() must always be called the same way.
color_cloud(
	myEmaFast,
	myEmaSlow,
	myShowFill ? '#00E676' : 'rgba(0,0,0,0)',
	myShowFill ? '#FF3D3D' : 'rgba(0,0,0,0)',
	'Bullish',
	'Bearish',
	0.12
);

// ---------------- SIGNALS (for Scanner/Alerts/Strategy) ----------------
const myBullishCross = for_every(myEmaFast, myEmaSlow, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _f > _s && myEmaFast[_i - 1] <= myEmaSlow[_i - 1];
});

const myBearishCross = for_every(myEmaFast, myEmaSlow, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _f < _s && myEmaFast[_i - 1] >= myEmaSlow[_i - 1];
});

const myBullishTrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f > _s);

register_signal(myBullishCross, 'Bullish Cross');
register_signal(myBearishCross, 'Bearish Cross');
register_signal(myBullishTrend, 'Bullish Trend');