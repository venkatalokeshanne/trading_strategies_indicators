describe_indicator('Timed MA Crossover', 'price');

// NOTE: This is a best-effort translation of the Pine Script strategy
// into a TrendSpider indicator. TrendSpider Custom JS does not support
// strategy.entry/strategy.close execution or bgcolor() shading like
// Pine Script does. Instead, this script paints the two moving
// averages and exposes the entry/exit conditions (date range + time
// window + crossover) as register_signal() outputs, so they can be
// used in Scanners, Alerts and the Strategy Tester.

const myMaTab = input.tab('Moving Averages');
const myMaRow = myMaTab.row();
const myFastMaLength = myMaRow.number('FastMA Length', 14, { min: 1 });
const mySlowMaLength = myMaRow.number('SlowMA Length', 28, { min: 1 });

const myDateTab = input.tab('Date Range');
const myFromRow = myDateTab.row();
const myFromMonth = myFromRow.number('From Month', 1, { min: 1, max: 12 });
const myFromDay = myFromRow.number('From Day', 1, { min: 1, max: 31 });
const myFromYear = myFromRow.number('From Year', 2021, { min: 1970, max: 2200 });

const myThruRow = myDateTab.row();
const myThruMonth = myThruRow.number('Thru Month', 1, { min: 1, max: 12 });
const myThruDay = myThruRow.number('Thru Day', 1, { min: 1, max: 31 });
const myThruYear = myThruRow.number('Thru Year', 2112, { min: 1970, max: 2200 });

const myTimeTab = input.tab('Time Range');
// Format: "HHMM-HHMM", e.g. "0930-1600". "0000-0000" means "anytime".
const myEntryTimeText = myTimeTab.text('Entry Time (HHMM-HHMM)', '0000-0000');
const myExitTimeText = myTimeTab.text('Exit Time (HHMM-HHMM)', '0000-0000');

// Date range boundaries, computed once (not using "new Date()").
const myStartTimestamp = Date.UTC(myFromYear, myFromMonth - 1, myFromDay, 0, 0, 0) / 1000;
const myFinishTimestamp = Date.UTC(myThruYear, myThruMonth - 1, myThruDay, 23, 59, 0) / 1000;

// Parses "HHMM-HHMM" into { fromMinutes, toMinutes }. Falls back to
// "anytime" (0 to 1439) if the text can't be parsed.
function myParseTimeRange(_text) {
	const myParts = String(_text).split('-');
	if (myParts.length !== 2 || myParts[0].length < 4 || myParts[1].length < 4) {
		return { fromMinutes: 0, toMinutes: 1439 };
	}
	const myFromH = parseInt(myParts[0].slice(0, 2), 10);
	const myFromM = parseInt(myParts[0].slice(2, 4), 10);
	const myToH = parseInt(myParts[1].slice(0, 2), 10);
	const myToM = parseInt(myParts[1].slice(2, 4), 10);
	if ([myFromH, myFromM, myToH, myToM].some(_v => isNaN(_v))) {
		return { fromMinutes: 0, toMinutes: 1439 };
	}
	return { fromMinutes: myFromH * 60 + myFromM, toMinutes: myToH * 60 + myToM };
}

const myEntryRange = myParseTimeRange(myEntryTimeText);
const myExitRange = myParseTimeRange(myExitTimeText);

// "0000-0000" means anytime, matching Pine Script's convention.
function myIsWithinTimeRange(_minutesOfDay, _range) {
	if (_range.fromMinutes === 0 && _range.toMinutes === 0) {
		return true;
	}
	if (_range.fromMinutes <= _range.toMinutes) {
		return _minutesOfDay >= _range.fromMinutes && _minutesOfDay <= _range.toMinutes;
	}
	// Overnight range (wraps past midnight)
	return _minutesOfDay >= _range.fromMinutes || _minutesOfDay <= _range.toMinutes;
}

const myFastMa = sma(close, myFastMaLength);
const mySlowMa = sma(close, mySlowMaLength);

// Crossover / crossunder of the two MAs.
const myEnterLong = for_every(myFastMa, mySlowMa, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _f > _s && myFastMa[_i - 1] <= mySlowMa[_i - 1];
});

const myExitLong = for_every(myFastMa, mySlowMa, (_f, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _f < _s && myFastMa[_i - 1] >= mySlowMa[_i - 1];
});

const myIsDateWithin = for_every(time, _t => _t >= myStartTimestamp && _t <= myFinishTimestamp);

const myIsEntryTimeWithin = time.map(_t => {
	const myParsedTime = time_of(_t);
	return myIsWithinTimeRange(myParsedTime.hours * 60 + myParsedTime.minutes, myEntryRange);
});

const myIsExitTimeWithin = time.map(_t => {
	const myParsedTime = time_of(_t);
	return myIsWithinTimeRange(myParsedTime.hours * 60 + myParsedTime.minutes, myExitRange);
});

const myEntrySignal = for_every(myIsDateWithin, myEnterLong, (_date, _cross, _prev, _i) => _date && myIsEntryTimeWithin[_i] && _cross);
const myExitSignal = for_every(myIsDateWithin, myExitLong, (_date, _cross, _prev, _i) => _date && myIsExitTimeWithin[_i] && _cross);

paint(myFastMa, { name: 'FastMA', color: '#f6c90e', thickness: 2, style: 'line' });
paint(mySlowMa, { name: 'SlowMA', color: '#00bcd4', thickness: 2, style: 'line' });

register_signal(myEntrySignal, 'Entry Long');
register_signal(myExitSignal, 'Exit Long');
register_signal(myIsDateWithin, 'Within Date Range');