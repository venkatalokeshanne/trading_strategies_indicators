describe_indicator('NQNMQS PDR PWR PMR', 'price');

// ===== Inputs =====
const dayTab = input.tab('Previous Day');
const myShowDay = dayTab.boolean('Show PDH PDL EQ', true);

const weekTab = input.tab('Previous Week');
const myShowWeek = weekTab.boolean('Show PWH PWL', true);

const monthTab = input.tab('Previous Month');
const myShowMonth = monthTab.boolean('Show PMH PML', true);

const styleTab = input.tab('Style');
const myShowLabels = styleTab.boolean('Show Labels', true);

const myN = close.length;

// Output level series (constant/stepped across the current period, representing
// the PREVIOUS completed period's High/Low, extended forward to the latest bar)
const myPdhLevel = series_of(null);
const myPdlLevel = series_of(null);
const myEqLevel = series_of(null);
const myPwhLevel = series_of(null);
const myPwlLevel = series_of(null);
const myPmhLevel = series_of(null);
const myPmlLevel = series_of(null);

assert(myN > 0, 'No data available');

const myFirstTime = time_of(time[0]);
const myDayKeyOf = _t => `${_t.year}-${_t.dayOfYear}`;
const myWeekKeyOf = _t => `${_t.year}-${_t.weekOfYear}`;
const myMonthKeyOf = _t => `${_t.year}-${_t.month}`;

// Day tracking
let myCurDayKey = myDayKeyOf(myFirstTime);
let myCurDayH = high[0];
let myCurDayL = low[0];
let myPrevDayH = null;
let myPrevDayL = null;

// Week tracking
let myCurWeekKey = myWeekKeyOf(myFirstTime);
let myCurWeekH = high[0];
let myCurWeekL = low[0];
let myPrevWeekH = null;
let myPrevWeekL = null;

// Month tracking
let myCurMonthKey = myMonthKeyOf(myFirstTime);
let myCurMonthH = high[0];
let myCurMonthL = low[0];
let myPrevMonthH = null;
let myPrevMonthL = null;

myPdhLevel[0] = null;
myPdlLevel[0] = null;
myEqLevel[0] = null;
myPwhLevel[0] = null;
myPwlLevel[0] = null;
myPmhLevel[0] = null;
myPmlLevel[0] = null;

for (let myIndex = 1; myIndex < myN; myIndex += 1) {
	const myT = time_of(time[myIndex]);

	// Day roll
	const myDayKey = myDayKeyOf(myT);
	if (myDayKey !== myCurDayKey) {
		myPrevDayH = myCurDayH;
		myPrevDayL = myCurDayL;
		myCurDayKey = myDayKey;
		myCurDayH = high[myIndex];
		myCurDayL = low[myIndex];
	}
	else {
		myCurDayH = Math.max(myCurDayH, high[myIndex]);
		myCurDayL = Math.min(myCurDayL, low[myIndex]);
	}

	// Week roll
	const myWeekKey = myWeekKeyOf(myT);
	if (myWeekKey !== myCurWeekKey) {
		myPrevWeekH = myCurWeekH;
		myPrevWeekL = myCurWeekL;
		myCurWeekKey = myWeekKey;
		myCurWeekH = high[myIndex];
		myCurWeekL = low[myIndex];
	}
	else {
		myCurWeekH = Math.max(myCurWeekH, high[myIndex]);
		myCurWeekL = Math.min(myCurWeekL, low[myIndex]);
	}

	// Month roll
	const myMonthKey = myMonthKeyOf(myT);
	if (myMonthKey !== myCurMonthKey) {
		myPrevMonthH = myCurMonthH;
		myPrevMonthL = myCurMonthL;
		myCurMonthKey = myMonthKey;
		myCurMonthH = high[myIndex];
		myCurMonthL = low[myIndex];
	}
	else {
		myCurMonthH = Math.max(myCurMonthH, high[myIndex]);
		myCurMonthL = Math.min(myCurMonthL, low[myIndex]);
	}

	myPdhLevel[myIndex] = myPrevDayH;
	myPdlLevel[myIndex] = myPrevDayL;
	myEqLevel[myIndex] = (myPrevDayH != null && myPrevDayL != null) ? (myPrevDayH + myPrevDayL) / 2 : null;
	myPwhLevel[myIndex] = myPrevWeekH;
	myPwlLevel[myIndex] = myPrevWeekL;
	myPmhLevel[myIndex] = myPrevMonthH;
	myPmlLevel[myIndex] = myPrevMonthL;
}

// ===== Paint lines (ladder = stepped, no interpolation, matches Pine's extend.right behavior) =====
const myPdhPainted = paint(myShowDay ? myPdhLevel : constants.empty_series, { name: 'PDH', style: 'ladder', color: '#2962FF', thickness: 1 });
const myPdlPainted = paint(myShowDay ? myPdlLevel : constants.empty_series, { name: 'PDL', style: 'ladder', color: '#D50000', thickness: 1 });
const myEqPainted = paint(myShowDay ? myEqLevel : constants.empty_series, { name: 'EQ', style: 'ladder', color: '#9E9E9E', thickness: 1 });

const myPwhPainted = paint(myShowWeek ? myPwhLevel : constants.empty_series, { name: 'PWH', style: 'ladder', color: '#00897B', thickness: 1 });
const myPwlPainted = paint(myShowWeek ? myPwlLevel : constants.empty_series, { name: 'PWL', style: 'ladder', color: '#F4511E', thickness: 1 });

const myPmhPainted = paint(myShowMonth ? myPmhLevel : constants.empty_series, { name: 'PMH', style: 'ladder', color: '#6A1B9A', thickness: 1 });
const myPmlPainted = paint(myShowMonth ? myPmlLevel : constants.empty_series, { name: 'PML', style: 'ladder', color: '#F9A825', thickness: 1 });

// Labels with the price value, placed on the last candle
if (myShowLabels) {
	const myLastIndex = myN - 1;
	const myDecimals = current.decimals || 2;

	if (myShowDay && myPdhLevel[myLastIndex] != null) {
		paint_label_at_line(myPdhPainted, myLastIndex, `PDH ${myPdhLevel[myLastIndex].toFixed(myDecimals)}`, { color: '#2962FF' });
	}
	if (myShowDay && myPdlLevel[myLastIndex] != null) {
		paint_label_at_line(myPdlPainted, myLastIndex, `PDL ${myPdlLevel[myLastIndex].toFixed(myDecimals)}`, { color: '#D50000' });
	}
	if (myShowDay && myEqLevel[myLastIndex] != null) {
		paint_label_at_line(myEqPainted, myLastIndex, `EQ ${myEqLevel[myLastIndex].toFixed(myDecimals)}`, { color: '#9E9E9E' });
	}
	if (myShowWeek && myPwhLevel[myLastIndex] != null) {
		paint_label_at_line(myPwhPainted, myLastIndex, `PWH ${myPwhLevel[myLastIndex].toFixed(myDecimals)}`, { color: '#00897B' });
	}
	if (myShowWeek && myPwlLevel[myLastIndex] != null) {
		paint_label_at_line(myPwlPainted, myLastIndex, `PWL ${myPwlLevel[myLastIndex].toFixed(myDecimals)}`, { color: '#F4511E' });
	}
	if (myShowMonth && myPmhLevel[myLastIndex] != null) {
		paint_label_at_line(myPmhPainted, myLastIndex, `PMH ${myPmhLevel[myLastIndex].toFixed(myDecimals)}`, { color: '#6A1B9A' });
	}
	if (myShowMonth && myPmlLevel[myLastIndex] != null) {
		paint_label_at_line(myPmlPainted, myLastIndex, `PML ${myPmlLevel[myLastIndex].toFixed(myDecimals)}`, { color: '#F9A825' });
	}
}

// ===== Scanner / Strategy signals (breakouts of each level) =====
const myCrossAbovePdh = for_every(close, myPdhLevel, (_c, _l, _p, _i) => _l != null && _i > 0 && close[_i - 1] <= myPdhLevel[_i - 1] && _c > _l);
const myCrossBelowPdl = for_every(close, myPdlLevel, (_c, _l, _p, _i) => _l != null && _i > 0 && close[_i - 1] >= myPdlLevel[_i - 1] && _c < _l);
const myCrossAbovePwh = for_every(close, myPwhLevel, (_c, _l, _p, _i) => _l != null && _i > 0 && close[_i - 1] <= myPwhLevel[_i - 1] && _c > _l);
const myCrossBelowPwl = for_every(close, myPwlLevel, (_c, _l, _p, _i) => _l != null && _i > 0 && close[_i - 1] >= myPwlLevel[_i - 1] && _c < _l);
const myCrossAbovePmh = for_every(close, myPmhLevel, (_c, _l, _p, _i) => _l != null && _i > 0 && close[_i - 1] <= myPmhLevel[_i - 1] && _c > _l);
const myCrossBelowPml = for_every(close, myPmlLevel, (_c, _l, _p, _i) => _l != null && _i > 0 && close[_i - 1] >= myPmlLevel[_i - 1] && _c < _l);

register_signal(myCrossAbovePdh, 'Cross Above PDH');
register_signal(myCrossBelowPdl, 'Cross Below PDL');
register_signal(myCrossAbovePwh, 'Cross Above PWH');
register_signal(myCrossBelowPwl, 'Cross Below PWL');
register_signal(myCrossAbovePmh, 'Cross Above PMH');
register_signal(myCrossBelowPml, 'Cross Below PML');