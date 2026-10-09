// This script is a near-literal translation of a trivial Pine Script demo
// strategy ("enter on bar 0, close on bar 1"). It does not represent any
// real trading logic. It is provided only to replicate the exact bars
// on which the original Pine script would fire its entry and exit.
describe_indicator('Deprecated Demo Entry Exit', 'lower');

// Entry signal fires only on the very first candle of the data set
// (bar_index == 0 in Pine).
const myEntrySignal = for_every(close, (_c, _prev, _index) => _index === 0);

// Exit signal fires only on the second candle of the data set
// (bar_index == 1 in Pine).
const myExitSignal = for_every(close, (_c, _prev, _index) => _index === 1);

// Register signals so they can be used in Scanners, Alerts and Strategy Tester.
register_signal(myEntrySignal, 'Entry Demo');
register_signal(myExitSignal, 'Exit Demo');

// Visual markers on the chart to confirm the exact bars where the
// signals fire, since the original Pine script had no visible plot
// (it used plot(na, display=display.none)).
const myEntryMarks = for_every(myEntrySignal, _e => _e ? 1 : null);
const myExitMarks = for_every(myExitSignal, _e => _e ? -1 : null);

paint(myEntryMarks, { name: 'Entry', style: 'labels_above', color: '#26A69A', thickness: 2 });
paint(myExitMarks, { name: 'Exit', style: 'labels_below', color: '#EF5350', thickness: 2 });