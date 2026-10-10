describe_indicator('Institutional RSI Trend Suite v2', 'lower');

// ─── Timeframe ───
const myTfTab = input.tab('Timeframe');
const myTfOptions = [''].concat(constants.time_frames);
// Shortened title; long input titles throw "name is too lengthy" errors
const myTf = myTfTab.select('RSI Timeframe', '', myTfOptions);

// ─── RSI settings ───
const myRsiTab = input.tab('Multiple RSI Settings');
const myRsi1Row = myRsiTab.row();
const myShowRsi1 = myRsi1Row.boolean('Show RSI 1', true);
const myRsiLen1 = myRsi1Row.number('RSI 1 Length', 21, { min: 1, max: 200 });
const myRsi2Row = myRsiTab.row();
const myShowRsi2 = myRsi2Row.boolean('Show RSI 2', true);
const myRsiLen2 = myRsi2Row.number('RSI 2 Length', 14, { min: 1, max: 200 });
const myRsi3Row = myRsiTab.row();
const myShowRsi3 = myRsi3Row.boolean('Show RSI 3', true);
const myRsiLen3 = myRsi3Row.number('RSI 3 Length', 7, { min: 1, max: 200 });

// ─── Moving average settings ───
const myMaTab = input.tab('RSI Moving Averages');
const myEmaLen = myMaTab.number('EMA Length', 3, { min: 1, max: 200 });
const myWmaLen = myMaTab.number('WMA Length', 21, { min: 1, max: 200 });
const myDemaLen = myMaTab.number('DEMA Length', 50, { min: 1, max: 200 });
// Shortened title
const myPrimaryRsiChoice = myMaTab.select('Primary RSI', 'RSI 1', ['RSI 1', 'RSI 2', 'RSI 3']);
const myMaShowRow = myMaTab.row();
const myShowEma = myMaShowRow.boolean('Show EMA', true);
const myShowWma = myMaShowRow.boolean('Show WMA', true);
const myShowDema = myMaShowRow.boolean('Show DEMA', true);

// ─── Levels ───
const myLevelsTab = input.tab('RSI Levels');
const myObLevel = myLevelsTab.number('Overbought Level', 70, { min: 1, max: 100 });
const myUpperLevel = myLevelsTab.number('Upper Range Level', 60, { min: 1, max: 100 });
const myMidLevel = myLevelsTab.number('Middle Level', 50, { min: 1, max: 100 });
const myLowerLevel = myLevelsTab.number('Lower Range Level', 40, { min: 1, max: 100 });
const myOsLevel = myLevelsTab.number('Oversold Level', 30, { min: 1, max: 100 });

// ─── Fetch data for the selected timeframe (if any) ───
const myUseOtherTf = myTf !== '';
const myOtherTfData = myUseOtherTf ? await request.history(current.ticker, myTf) : null;
assert(!myUseOtherTf || !myOtherTfData.error, `Error fetching data: "${myOtherTfData && myOtherTfData.error}"`);
const myCloseSource = myUseOtherTf ? myOtherTfData.close : close;

// ─── Compute the three RSIs on their native series, then land onto current chart ───
const myRawRsi1 = rsi(myCloseSource, myRsiLen1);
const myRawRsi2 = rsi(myCloseSource, myRsiLen2);
const myRawRsi3 = rsi(myCloseSource, myRsiLen3);

function myLandIfNeeded(_series) {
	if (!myUseOtherTf) {
		return _series;
	}
	const myLanded = land_points_onto_series(myOtherTfData.time, _series, time, 'ge');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myRsi1 = myLandIfNeeded(myRawRsi1);
const myRsi2 = myLandIfNeeded(myRawRsi2);
const myRsi3 = myLandIfNeeded(myRawRsi3);

// ─── Primary RSI selection ───
const myPrimaryRsi = myPrimaryRsiChoice === 'RSI 1' ? myRsi1 : (myPrimaryRsiChoice === 'RSI 2' ? myRsi2 : myRsi3);

// ─── Moving averages of the primary RSI ───
const myEmaRsi = ema(myPrimaryRsi, myEmaLen);
const myWmaRsi = wma(myPrimaryRsi, myWmaLen);
const myDemaEma1 = ema(myPrimaryRsi, myDemaLen);
const myDemaEma2 = ema(myDemaEma1, myDemaLen);
const myDemaRsi = sub(mult(myDemaEma1, 2), myDemaEma2);

// ─── RSI plots ───
paint(myShowRsi1 ? myRsi1 : constants.empty_series, { name: 'RSI1', color: '#1E88E5', thickness: 2 });
paint(myShowRsi2 ? myRsi2 : constants.empty_series, { name: 'RSI2', color: '#FB8C00', thickness: 2 });
paint(myShowRsi3 ? myRsi3 : constants.empty_series, { name: 'RSI3', color: '#8E24AA', thickness: 2 });

// ─── Moving average plots ───
paint(myShowEma ? myEmaRsi : constants.empty_series, { name: 'EMA', color: '#1E88E5', thickness: 2 });
paint(myShowWma ? myWmaRsi : constants.empty_series, { name: 'WMA', color: '#FB8C00', thickness: 2 });
paint(myShowDema ? myDemaRsi : constants.empty_series, { name: 'DEMA', color: '#2E7D32', thickness: 2 });

// ─── Reference levels ───
paint(horizontal_line(myObLevel), { name: 'Overbought', color: 'red', style: 'dotted', thickness: 1 });
paint(horizontal_line(myUpperLevel), { name: 'Bull Range', color: 'rgba(0,200,0,0.5)', style: 'dotted', thickness: 1 });
paint(horizontal_line(myLowerLevel), { name: 'Bear Range', color: 'rgba(200,0,0,0.5)', style: 'dotted', thickness: 1 });
paint(horizontal_line(myOsLevel), { name: 'Oversold', color: 'green', style: 'dotted', thickness: 1 });
paint(horizontal_line(myMidLevel), { name: 'Center', color: 'gray', thickness: 1 });

// ─── Fill between primary RSI and the center line, colored by position ───
color_cloud(
	myPrimaryRsi,
	horizontal_line(myMidLevel),
	'rgba(0,200,0,0.15)',
	'rgba(200,0,0,0.15)',
	'AboveCenter',
	'BelowCenter'
);

// ─── Scanning / strategy signals ───
register_signal(for_every(myPrimaryRsi, _r => _r > myObLevel), 'Primary RSI Overbought');
register_signal(for_every(myPrimaryRsi, _r => _r < myOsLevel), 'Primary RSI Oversold');
register_signal(
	for_every(myPrimaryRsi, (_r, _prev, _i) => _i > 0 && _r > myMidLevel && myPrimaryRsi[_i - 1] <= myMidLevel),
	'Primary RSI Crossed Above Center'
);
register_signal(
	for_every(myPrimaryRsi, (_r, _prev, _i) => _i > 0 && _r < myMidLevel && myPrimaryRsi[_i - 1] >= myMidLevel),
	'Primary RSI Crossed Below Center'
);
register_signal(for_every(myPrimaryRsi, _r => _r > myUpperLevel), 'Primary RSI In Bull Range');
register_signal(for_every(myPrimaryRsi, _r => _r < myLowerLevel), 'Primary RSI In Bear Range');