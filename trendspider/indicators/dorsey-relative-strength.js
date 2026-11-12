<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Dorsey Relative Strength', 'lower', { decimals: 3, shortName: 'RSD'});

const indexSymbol = input.symbol('Index');

// Convert current resolution to a higher one that contains at least double the amount of candles
const higherResolution = { 1: '2', 2: '4', 3: '6', 4: '10', 5: '10', 6: '12', 10: '30', 12: '30',	15: '30', 30: '60', 45: '90', 60: '120', 65: '240', 90: '240', 120: '240', 240: '1440', 1440: 'D',	D: 'W', W: 'M', M: 'Q', Q: 'Y', Y: 'Y' }[constants.resolution];

const indexData = await request.history(indexSymbol, higherResolution, {	ext_session: constants.session.lengthMinutes == constants.ext_session.lengthMinutes});

const indexClose = land_points_onto_series(indexData.time, indexData.close, time, 'ge');

const rsd = mult(div(close, interpolate_sparse_series(indexClose, 'constant')), 100);

paint(rsd, { name: 'Line', color: 'grey', thickness: 5 });
</code>