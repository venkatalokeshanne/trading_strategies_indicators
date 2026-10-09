describe_indicator('HTF CHOC detector by Tao Woy', 'price');

// The provided Pine Script is a discontinued placeholder version.
// It contains no actual CHOC (Change of Character) detection logic;
// it only displays a note table pointing users to a newer, protected
// version named "HTF CHOC by Tao Woy". Since there is no computational
// logic (no plots, no alerts, no signals) in the original script,
// there is nothing meaningful to map to scanner or strategy signals.
// This port simply reproduces the note-table behavior using an overlay.

paint_overlay('HTFCHOCNote', { position: 'top_right' }, {
	rows: [{
		cells: [{
			text: 'New version: HTF CHOC by Tao Woy\nSearch: HTF CHOC by Tao Woy (angkoon167)',
			color: 'gray'
		}]
	}]
});

// No real signal exists in the source script, so a constant false signal
// is registered to keep the indicator usable in Visual Scripts, while
// accurately reflecting that there is no detection logic to expose.
const myNoSignal = series_of(false);
register_signal(myNoSignal, 'No Signal Available');