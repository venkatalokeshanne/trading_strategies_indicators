describe_indicator('Volume Previous Bar Comparison', 'lower');

// Compares current bar volume to the previous bar volume.
// Green/teal when volume increased vs prior bar, red when it decreased or stayed the same.
const myIsGrow = for_every(volume, (_v, _p, _i) => {
	if (_i === 0) return false;
	return _v > volume[_i - 1];
});

const myVolColor = for_every(myIsGrow, _g => _g ? '#26A69A' : '#EF5350');

paint(volume, { name: 'Volume', style: 'column', color: myVolColor });

// Signal for scanners/alerts/strategies: volume grew vs previous bar
register_signal(myIsGrow, 'Volume Increased vs Previous Bar');

// Signal for the opposite case: volume did not grow vs previous bar
const myIsFall = for_every(myIsGrow, _g => !_g);
register_signal(myIsFall, 'Volume Not Increased vs Previous Bar');