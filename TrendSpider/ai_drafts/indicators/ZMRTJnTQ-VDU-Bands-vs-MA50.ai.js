describe_indicator('VDU Bands (vs MA50)', 'lower', { format: 'volume' });

// Volume MA length, user configurable
const myMaLen = input.number('Volume MA Length', 50, { min: 1, max: 500 });
const myVolMa = sma(volume, myMaLen);
const myPct = div(volume, myVolMa);

// Color buckets exactly matching the Pine Script thresholds
const myVolumeColor = for_every(myPct, _p => {
	if (_p === null) return null;
	if (_p <= 0.50) return '#0000FF';       // True VDU <=50%
	if (_p <= 0.60) return '#800080';       // 50-60%
	if (_p <= 0.70) return '#808000';       // 60-70%
	if (_p <= 1.00) return 'rgba(128,128,128,0.6)'; // 70-100% (40% transparency approx)
	return 'rgba(255,0,0,0.8)';             // >100% (20% transparency approx)
});

paint(volume, { name: 'Volume', style: 'column', color: myVolumeColor });
paint(myVolMa, { name: 'MA50Vol', color: 'orange', thickness: 2 });

// True VDU marker (pct <= 0.50), shown as labels above
// Renamed this painted series to "TrueVduMarker" so it does not
// collide (same name) with the "True VDU" signal registered below.
const myTrueVduMarks = for_every(myPct, _p => _p !== null && _p <= 0.50 ? volume : null);
paint(myTrueVduMarks, { name: 'TrueVduMarker', style: 'labels_above', color: 'blue' });

// Signals for scanner/alerts/strategy usage
const mySignalTrueVdu = for_every(myPct, _p => _p !== null && _p <= 0.50);
const mySignalModerateVdu = for_every(myPct, _p => _p !== null && _p > 0.50 && _p <= 0.60);
const mySignalMildVdu = for_every(myPct, _p => _p !== null && _p > 0.60 && _p <= 0.70);
const mySignalNormalVolume = for_every(myPct, _p => _p !== null && _p > 0.70 && _p <= 1.00);
const mySignalHighVolume = for_every(myPct, _p => _p !== null && _p > 1.00);

register_signal(mySignalTrueVdu, 'True VDU');
register_signal(mySignalModerateVdu, 'Moderate VDU');
register_signal(mySignalMildVdu, 'Mild VDU');
register_signal(mySignalNormalVolume, 'Normal Volume');
register_signal(mySignalHighVolume, 'High Volume');