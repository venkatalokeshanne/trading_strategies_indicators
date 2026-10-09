describe_indicator('Andrey Colored Volume', 'lower');

// Replicates Pine Script volume coloring: green if volume increased,
// red if volume decreased, yellow if unchanged versus previous candle.
const myVolume = volume;
const myPrevVolume = shift(volume, 1);

const myVolumeColor = for_every(myVolume, myPrevVolume, (_vol, _prevVol) => {
	if (_vol > _prevVol) return 'green';
	if (_vol < _prevVol) return 'red';
	return 'yellow';
});

paint(myVolume, { name: 'Volume', style: 'column', color: myVolumeColor });

// Signals for scanner/alerts/strategy usage
const myVolumeUpSignal = for_every(myVolume, myPrevVolume, (_vol, _prevVol) => _vol > _prevVol);
const myVolumeDownSignal = for_every(myVolume, myPrevVolume, (_vol, _prevVol) => _vol < _prevVol);
const myVolumeFlatSignal = for_every(myVolume, myPrevVolume, (_vol, _prevVol) => _vol === _prevVol);

register_signal(myVolumeUpSignal, 'Volume Up');
register_signal(myVolumeDownSignal, 'Volume Down');
register_signal(myVolumeFlatSignal, 'Volume Flat');