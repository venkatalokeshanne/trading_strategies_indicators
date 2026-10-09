describe_indicator('BNC Contrarian', 'lower');

// ── EMOTION SCORE ──────────────────────────────────────
const myRsi = rsi(close, 14);
const myStoch = stochastic(myRsi, myRsi, myRsi, 14);
const mySk = ema(myStoch, 3);

// Stoch RSI normalized: only <10 and >90 push the extremes,
// everything in between maps to neutral (50)
const mySkNorm = for_every(mySk, _sk => _sk > 90 ? 100 : (_sk < 10 ? 0 : 50));

const myEma20 = ema(close, 20);
const myDev = for_every(close, myEma20, (_c, _e) => Math.min(Math.max((_c - _e) / _e * 500 + 50, 0), 100));

// Weekly RSI, fetched without lookahead: we land each weekly bar's
// value onto the LAST timestamp <= it ("le") and hold it constant
// until the next weekly bar closes, matching Pine's lookahead_off.
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, 'Error fetching weekly data: ' + myWeeklyData.error);
const myWeeklyRsi = rsi(myWeeklyData.close, 14);
const myWeeklyRsiLanded = land_points_onto_series(myWeeklyData.time, myWeeklyRsi, time, 'le');
const myWeeklyRsiOnChart = interpolate_sparse_series(myWeeklyRsiLanded, 'constant');

const myEmotion = for_every(
	myWeeklyRsiOnChart, myRsi, mySkNorm, myDev,
	(_rw, _r, _skn, _d) => (_rw * 0.40) + (_r * 0.25) + (_skn * 0.25) + (_d * 0.10)
);

// ── STATE MACHINE ──────────────────────────────────────
// 0: neutral, 1: in FOMO (waiting to fade), 2: in PANIC (waiting to fade), 3: cooldown
const mySellSignal = series_of(false);
const myBuySignal = series_of(false);

let myState = 0;
for (let myIndex = 0; myIndex < myEmotion.length; myIndex += 1) {
	const myValue = myEmotion[myIndex];
	const myInFomo = myValue > 75;
	const myInPanic = myValue < 25;
	const myInNeutral = myValue >= 35 && myValue <= 65;

	if (myState === 0 && myInFomo) {
		myState = 1;
	}
	if (myState === 0 && myInPanic) {
		myState = 2;
	}

	const mySell = myState === 1 && !myInFomo;
	const myBuy = myState === 2 && !myInPanic;

	mySellSignal[myIndex] = mySell;
	myBuySignal[myIndex] = myBuy;

	if (mySell) {
		myState = 3;
	}
	if (myBuy) {
		myState = 3;
	}

	if (myState === 3 && myInNeutral) {
		myState = 0;
	}
}

register_signal(mySellSignal, 'Fade FOMO Sell Signal');
register_signal(myBuySignal, 'Fade Panic Buy Signal');

// ── PLOT ───────────────────────────────────────────────
const myBarColor = for_every(myEmotion, _e => {
	if (_e > 75) return '#ff0000';
	if (_e > 60) return '#ffa500';
	if (_e > 50) return '#ffd400';
	if (_e > 40) return '#008080';
	if (_e > 25) return '#00ffff';
	return '#00ff00';
});

paint(myEmotion, { name: 'Emotion', style: 'column', color: myBarColor, thickness: 1 });
paint(myEmotion, { name: 'Emotion Line', style: 'line', color: myBarColor, thickness: 1 });

paint(horizontal_line(75), { name: 'Do Not Long', color: '#ff0000', style: 'line' });
paint(horizontal_line(50), { name: 'Neutral', color: 'gray', style: 'dotted' });
paint(horizontal_line(25), { name: 'Do Not Short', color: '#00ff00', style: 'line' });

fill(
	paint(horizontal_line(100), { name: 'Upper Band', hidden: true }),
	paint(horizontal_line(75), { name: 'Upper Band Base', hidden: true }),
	'red',
	0.12
);
fill(
	paint(horizontal_line(25), { name: 'Lower Band Base', hidden: true }),
	paint(horizontal_line(0), { name: 'Lower Band', hidden: true }),
	'lime',
	0.12
);

// ── TABLE ──────────────────────────────────────────────
const myLastEmotion = myEmotion[myEmotion.length - 1];
const myStateTxt = myLastEmotion > 75 ? 'DO NOT LONG' : myLastEmotion > 55 ? 'CAUTION' : myLastEmotion > 45 ? 'NEUTRAL' : myLastEmotion > 25 ? 'CAUTION' : 'DO NOT SHORT';
const myActionTxt = myLastEmotion > 75 ? 'WAIT TO SELL' : myLastEmotion < 25 ? 'WAIT TO BUY' : 'NO EDGE';
const myStateBg = myLastEmotion > 75 ? '#cc0000' : myLastEmotion > 55 ? '#cc7a00' : myLastEmotion > 45 ? '#666666' : myLastEmotion > 25 ? '#007a7a' : '#00cc00';

paint_overlay('EmotionTable', { position: 'top_left' }, {
	rows: [{
		cells: [
			{ text: 'EMOTION', background_color: '#1a1a1a', color: '#cccccc' },
			{ text: String(Math.round(myLastEmotion)), background_color: '#1a1a1a', color: '#ffffff' }
		]
	}, {
		cells: [
			{ text: 'ZONE', background_color: '#1a1a1a', color: '#cccccc' },
			{ text: myStateTxt, background_color: myStateBg, color: '#ffffff' }
		]
	}, {
		cells: [
			{ text: 'ACTION', background_color: '#1a1a1a', color: '#cccccc' },
			{ text: myActionTxt, background_color: myStateBg, color: '#ffffff' }
		]
	}]
});