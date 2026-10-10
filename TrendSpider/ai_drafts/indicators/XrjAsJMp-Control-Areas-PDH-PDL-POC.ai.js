describe_indicator('Control Areas PDH PDL POC', 'price');
// Converts a Pine Script indicator that computes Previous Day High (PDH),
// Previous Day Low (PDL) and Point of Control (POC) using a 100 row volume
// profile built from chart bars of the closed day. Values freeze for the
// entire following day (no repaint), exactly like line.new/extend.right in
// Pine. Best used on timeframes <= 15m since the profile uses chart bars.
const myRows = input.number('Profile rows', 100, { min: 20, max: 200 });
const myShowLabels = input.boolean('Price labels', true);
const myLabelMode = input.select('Label text', 'Full', ['Full', 'Abbreviated']);
const myN = close.length;

// group candle indices by trading day (daily session id)
const mySessionIds = time.map(_t => bar_at(_t, 'D').session);
const myDayGroups = [];
for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (myDayGroups.length === 0 || myDayGroups[myDayGroups.length - 1].sessionId !== mySessionIds[myIndex]) {
		myDayGroups.push({ sessionId: mySessionIds[myIndex], indices: [] });
	}
	myDayGroups[myDayGroups.length - 1].indices.push(myIndex);
}

// builds the volume profile for one closed day and returns pdh/pdl/poc
function myComputeDayProfile(_indices) {
	const myHighs = _indices.map(_i => high[_i]);
	const myLows = _indices.map(_i => low[_i]);
	const myVols = _indices.map(_i => volume[_i]);
	const myLo = Math.min(...myLows);
	const myHi = Math.max(...myHighs);
	const myStep = (myHi - myLo) / myRows;

	if (!(myStep > 0)) {
		return { pdh: myHi, pdl: myLo, poc: (myHi + myLo) / 2 };
	}

	// avoid using "new Array(...)"; build a zero-filled array without "new"
	const myVolRows = Array(myRows).fill(0);

	for (let myBarIndex = 0; myBarIndex < _indices.length; myBarIndex += 1) {
		const myBl = myLows[myBarIndex];
		const myBh = myHighs[myBarIndex];
		const myBv = myVols[myBarIndex];
		const myR0 = Math.max(Math.floor((myBl - myLo) / myStep), 0);
		const myR1 = Math.min(Math.floor((myBh - myLo) / myStep), myRows - 1);

		for (let myRow = myR0; myRow <= myR1; myRow += 1) {
			const myLevel = myLo + myRow * myStep;
			const myProp = myBh <= myBl ? 1.0 : (Math.min(myBh, myLevel + myStep) - Math.max(myBl, myLevel)) / (myBh - myBl);
			myVolRows[myRow] += myBv * myProp;
		}
	}

	let myMaxRow = 0;
	for (let myRow = 1; myRow < myRows; myRow += 1) {
		if (myVolRows[myRow] > myVolRows[myMaxRow]) {
			myMaxRow = myRow;
		}
	}

	const myPoc = myLo + (myMaxRow + 0.5) * myStep;
	return { pdh: myHi, pdl: myLo, poc: myPoc };
}

const myPdhSeries = series_of(null);
const myPdlSeries = series_of(null);
const myPocSeries = series_of(null);

// each day (starting from the 2nd one) displays the profile of the
// previously closed day, frozen for the whole day - exactly as Pine's
// line.set_xy on newDay, with extend.right holding the value
for (let myDay = 1; myDay < myDayGroups.length; myDay += 1) {
	const myProfile = myComputeDayProfile(myDayGroups[myDay - 1].indices);
	for (const myIdx of myDayGroups[myDay].indices) {
		myPdhSeries[myIdx] = myProfile.pdh;
		myPdlSeries[myIdx] = myProfile.pdl;
		myPocSeries[myIdx] = myProfile.poc;
	}
}

const myPdhLine = paint(myPdhSeries, { name: 'PDH', color: 'red', thickness: 2, style: 'ladder' });
const myPdlLine = paint(myPdlSeries, { name: 'PDL', color: 'green', thickness: 2, style: 'ladder' });
const myPocLine = paint(myPocSeries, { name: 'POC', color: '#dddddd', thickness: 2, style: 'dotted' });

// labels at the last candle
const myLastIndex = myN - 1;
const myFull = myLabelMode === 'Full';
if (myShowLabels && myPdhSeries[myLastIndex] != null) {
	paint_label_at_line(myPdhLine, myLastIndex, (myFull ? 'Previous Day High ' : 'PDH ') + myPdhSeries[myLastIndex].toFixed(current.decimals), { color: 'red', background_color: 'red' });
	paint_label_at_line(myPdlLine, myLastIndex, (myFull ? 'Previous Day Low ' : 'PDL ') + myPdlSeries[myLastIndex].toFixed(current.decimals), { color: 'green', background_color: 'green' });
	paint_label_at_line(myPocLine, myLastIndex, (myFull ? 'Point of Control ' : 'POC ') + myPocSeries[myLastIndex].toFixed(current.decimals), { color: 'white', background_color: '#dddddd' });
}

// ── scanner / strategy signals ──────────────────────────────────────────
const myPrevClose = shift(close, 1);
const myPrevPdh = shift(myPdhSeries, 1);
const myPrevPdl = shift(myPdlSeries, 1);
const myPrevPoc = shift(myPocSeries, 1);

const myBreakAbovePdh = for_every(close, myPdhSeries, myPrevClose, myPrevPdh,
	(_c, _p, _pc, _pp) => _p != null && _pp != null && _c > _p && _pc <= _pp);
const myBreakBelowPdl = for_every(close, myPdlSeries, myPrevClose, myPrevPdl,
	(_c, _p, _pc, _pp) => _p != null && _pp != null && _c < _p && _pc >= _pp);
const myCrossAbovePoc = for_every(close, myPocSeries, myPrevClose, myPrevPoc,
	(_c, _p, _pc, _pp) => _p != null && _pp != null && _c > _p && _pc <= _pp);
const myCrossBelowPoc = for_every(close, myPocSeries, myPrevClose, myPrevPoc,
	(_c, _p, _pc, _pp) => _p != null && _pp != null && _c < _p && _pc >= _pp);

register_signal(myBreakAbovePdh, 'Close Breaks Above PDH');
register_signal(myBreakBelowPdl, 'Close Breaks Below PDL');
register_signal(myCrossAbovePoc, 'Close Crosses Above POC');
register_signal(myCrossBelowPoc, 'Close Crosses Below POC');