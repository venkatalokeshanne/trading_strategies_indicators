describe_indicator('Session Open Markers (Tashkent 1900 and 2200)', 'price');

// Pine Script uses time("", "Asia/Tashkent") to get hour/minute in the
// Tashkent time zone (UTC+5, no DST). The Custom JS API does not expose
// arbitrary time zone conversion (time_of/bar_at always use the exchange's
// own time zone), so we approximate by manually shifting each candle's
// Unix timestamp by +5 hours (Tashkent offset) before extracting hour
// and minute. This reproduces the exact Pine logic as long as Tashkent
// stays at UTC+5 (it has no DST, so this is historically accurate).
const myTashkentOffsetSeconds = 5 * 3600;

const myHourMinute = time.map(_t => {
	const myShifted = _t + myTashkentOffsetSeconds;
	const mySecondsOfDay = ((myShifted % 86400) + 86400) % 86400;
	const myHour = Math.floor(mySecondsOfDay / 3600);
	const myMinute = Math.floor((mySecondsOfDay % 3600) / 60);
	return { hour: myHour, minute: myMinute };
});

const myIsNineteen = myHourMinute.map(_hm => _hm.hour === 19 && _hm.minute === 0);
const myIsTwentyTwo = myHourMinute.map(_hm => _hm.hour === 22 && _hm.minute === 0);

// Build "vertical line" markers by painting the candle's high and low
// only on marked bars (null elsewhere), then filling between them.
// This reproduces the visual effect of Pine's line.new(bar_index, low,
// bar_index, high, ...) at the signal bar.
const myGreenHigh = for_every(high, myIsNineteen, (_h, _flag) => _flag ? _h : null);
const myGreenLow = for_every(low, myIsNineteen, (_l, _flag) => _flag ? _l : null);

const myRedHigh = for_every(high, myIsTwentyTwo, (_h, _flag) => _flag ? _h : null);
const myRedLow = for_every(low, myIsTwentyTwo, (_l, _flag) => _flag ? _l : null);

const myGreenHighPainted = paint(myGreenHigh, { name: 'GreenHigh', color: 'green', style: 'column', thickness: 2 });
const myGreenLowPainted = paint(myGreenLow, { name: 'GreenLow', color: 'green', style: 'column', thickness: 2 });
fill(myGreenHighPainted, myGreenLowPainted, 'green', 0.9);

const myRedHighPainted = paint(myRedHigh, { name: 'RedHigh', color: 'red', style: 'column', thickness: 2 });
const myRedLowPainted = paint(myRedLow, { name: 'RedLow', color: 'red', style: 'column', thickness: 2 });
fill(myRedHighPainted, myRedLowPainted, 'red', 0.9);

// Signals for use in Scanners, Alerts and the Strategy Tester.
register_signal(myIsNineteen, 'Session 1900 Tashkent');
register_signal(myIsTwentyTwo, 'Session 2200 Tashkent');