describe_indicator('ICT Killzones', 'price');

// NOTE: TrendSpider Custom JS has no box/label drawing primitives like
// Pine's box.new()/label.new(). This port approximates each killzone
// "box" using two filled lines (session high/low) and places a text
// label at the start of each session via paint_label_at_line(). The
// label size option from Pine is not supported here (no size param on
// paint_label_at_line), so it is accepted as an input but not applied.
// Session windows are computed by converting each candle's timestamp to
// America/New_York time using the moment-timezone library (the
// `time(timeframe.period, sessStr, tz)` Pine function has no direct
// equivalent, so this is a manual re-implementation of the same ICT
// killzone hour ranges).

const myKillzonesTab = input.tab('Killzones');
const myShowAsia = myKillzonesTab.boolean('Show Asia Killzone', true);
const myShowLondon = myKillzonesTab.boolean('Show London Killzone', true);
const myShowNYAM = myKillzonesTab.boolean('Show NY AM Killzone', true);
const myShowNYPM = myKillzonesTab.boolean('Show NY PM Killzone', false);
const myShowSB = myKillzonesTab.boolean('Show Silver Bullet Windows', true);

const myColorsTab = input.tab('Colors');
const myAsiaColor = myColorsTab.color('Asia', 'rgba(242,226,184,0.3)');
const myLondonColor = myColorsTab.color('London', 'rgba(88,166,255,0.3)');
const myNYAMColor = myColorsTab.color('NY AM', 'rgba(8,153,129,0.3)');
const myNYPMColor = myColorsTab.color('NY PM', 'rgba(210,153,34,0.3)');
const mySBColor = myColorsTab.color('Silver Bullet', 'rgba(242,54,69,0.45)');

const myDisplayTab = input.tab('Display');
const myShowLabels = myDisplayTab.boolean('Show Session Labels', true);
// Label size kept as an input for parity with the Pine script, but the
// Custom JS label API has no size control, so it has no visual effect.
const myLblSizeStr = myDisplayTab.select('Label Size', 'Normal', ['Tiny', 'Small', 'Normal', 'Large']);
const myShowHL = myDisplayTab.boolean('Show Killzone High/Low', true);
const myMaxDays = myDisplayTab.number('Days Back to Draw', 5, { min: 1, max: 20 });

const myMoment = library('moment-timezone');

// Convert each candle's timestamp to NY local hour (decimal).
const myNYHourDecimal = time.map(_t => {
	const myLocal = myMoment.tz(_t * 1000, 'America/New_York');
	return myLocal.hours() + (myLocal.minutes() / 60);
});

const myAsiaSess = myNYHourDecimal.map(_h => _h >= 20 && _h < 24);
const myLondonSess = myNYHourDecimal.map(_h => _h >= 2 && _h < 5);
const myNYAMSess = myNYHourDecimal.map(_h => _h >= 7 && _h < 10);
const myNYPMSess = myNYHourDecimal.map(_h => _h >= 13.5 && _h < 16);
const mySB1 = myNYHourDecimal.map(_h => _h >= 3 && _h < 4);
const mySB2 = myNYHourDecimal.map(_h => _h >= 10 && _h < 11);
const mySB3 = myNYHourDecimal.map(_h => _h >= 14 && _h < 15);
const mySBSess = mySB1.map((_v, _i) => _v || mySB2[_i] || mySB3[_i]);

const myCutoff = current.now - (myMaxDays * 86400);
const myRecent = time.map(_t => _t > myCutoff);

// Builds the per-candle "box" top/bottom lines for a killzone session.
function buildMyZone(mySessionActive) {
	const myTop = series_of(null);
	const myBottom = series_of(null);
	const myStartFlags = series_of(false);
	let myHigh = null;
	let myLow = null;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const myActive = mySessionActive[myIndex] && myRecent[myIndex];
		const myPrevActive = myIndex > 0 ? (mySessionActive[myIndex - 1] && myRecent[myIndex - 1]) : false;

		if (myActive && !myPrevActive) {
			myHigh = high[myIndex];
			myLow = low[myIndex];
			myStartFlags[myIndex] = true;
		}
		else if (myActive && myShowHL) {
			myHigh = Math.max(myHigh, high[myIndex]);
			myLow = Math.min(myLow, low[myIndex]);
		}

		if (myActive) {
			myTop[myIndex] = myHigh;
			myBottom[myIndex] = myLow;
		}
	}

	return { top: myTop, bottom: myBottom, startFlags: myStartFlags };
}

function paintMyZone(myEnabled, mySessionArr, myColor, myLabelText) {
	const myZone = buildMyZone(mySessionArr.map((_v, _i) => _v && myEnabled));

	const myTopPainted = paint(myZone.top, { name: myLabelText + 'Top', color: myColor, style: 'ladder' });
	const myBottomPainted = paint(myZone.bottom, { name: myLabelText + 'Bottom', color: myColor, style: 'ladder' });
	fill(myTopPainted, myBottomPainted, myColor, 0.25);

	if (myShowLabels) {
		for (let myIndex = 0; myIndex < myZone.startFlags.length; myIndex += 1) {
			if (myZone.startFlags[myIndex]) {
				paint_label_at_line(myTopPainted, myIndex, myLabelText, { background_color: myColor, color: 'white', vertical_align: 'top' });
			}
		}
	}

	return mySessionArr.map((_v, _i) => _v && myEnabled);
}

const myAsiaActive = paintMyZone(myShowAsia, myAsiaSess, myAsiaColor, 'ASIA');
const myLondonActive = paintMyZone(myShowLondon, myLondonSess, myLondonColor, 'LONDON');
const myNYAMActive = paintMyZone(myShowNYAM, myNYAMSess, myNYAMColor, 'NYAM');
const myNYPMActive = paintMyZone(myShowNYPM, myNYPMSess, myNYPMColor, 'NYPM');

// Silver Bullet background approximated via candle coloring (no bgcolor
// equivalent exists in Custom JS API).
const myIsIntraday = !isNaN(current.resolution);
const mySBColors = for_every(close, (_c, _p, _i) => {
	const myActive = myShowSB && mySBSess[_i] && myRecent[_i] && myIsIntraday;
	return myActive ? mySBColor : null;
});
color_candles(mySBColors);

// ─── Signals for scanners / alerts / strategies ──────────────────────────
const myLondonOpen = for_every(series_of(0), (_x, _p, _i) => myLondonActive[_i] && !(_i > 0 && myLondonActive[_i - 1]));
const myNYAMOpen = for_every(series_of(0), (_x, _p, _i) => myNYAMActive[_i] && !(_i > 0 && myNYAMActive[_i - 1]));
const mySBOpen = for_every(series_of(0), (_x, _p, _i) => (myShowSB && mySBSess[_i]) && !(_i > 0 && myShowSB && mySBSess[_i - 1]));
const myAsiaOpen = for_every(series_of(0), (_x, _p, _i) => myAsiaActive[_i] && !(_i > 0 && myAsiaActive[_i - 1]));
const myNYPMOpen = for_every(series_of(0), (_x, _p, _i) => myNYPMActive[_i] && !(_i > 0 && myNYPMActive[_i - 1]));

register_signal(myAsiaOpen, 'Asia Killzone Open');
register_signal(myLondonOpen, 'London Killzone Open');
register_signal(myNYAMOpen, 'NY AM Killzone Open');
register_signal(myNYPMOpen, 'NY PM Killzone Open');
register_signal(mySBOpen, 'Silver Bullet Window Open');