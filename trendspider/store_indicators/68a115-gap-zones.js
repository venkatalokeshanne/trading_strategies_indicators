<code x-ref="code" class="hljs" data-clipboard-text>// ░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓████████▓▒░       ░▒▓███████▓▒░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓███████▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓██████▓▒░         ░▒▓██████▓▒░░▒▓██████▓▒░ ░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░ ░▒▓██████▓▒░  
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓████████▓▒░      ░▒▓███████▓▒░░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░                                                                                                                                                                      

describe_indicator('Gap Zones', {decimals: 2});

const maxZones = 5;
const zoneColor = 'rgba(0, 150, 136, 0.2)'
const midlineColor = 'rgba(0, 150, 136, 0.5)'

// inputs
const timeframe = input.select('Timeframe', 'W', constants.time_frames);

// logic
const data = await request.history(current.ticker, timeframe);
assert(!data.error, `Error fetching data: ${data.error}`);

const zones = [];
let lastClose = null;

for (let i = 1; i < data.close.length; i++) {
    const prevClose = data.close[i - 1];
    const currOpen = data.open[i];
    
    if (prevClose !== currOpen) {
        zones.push({
            start: data.time[i],
            high: Math.max(prevClose, currOpen),
            low: Math.min(prevClose, currOpen),
            mid: (prevClose + currOpen) / 2
        });
    }
    
    lastClose = data.close[i];
}

const activeZones = [];

for (let i = zones.length - 1; i >= 0 && activeZones.length < maxZones; i--) {
    const zone = zones[i];
    
    // Check if this zone engulfs any previous active zones
    const engulfedIndex = activeZones.findIndex(az => 
        zone.high >= az.high && zone.low <= az.low
    );
    
    if (engulfedIndex !== -1) {
        activeZones.splice(engulfedIndex);
    }
    
    activeZones.unshift(zone);
}

// plots
for (let zoneItr = 0; zoneItr < activeZones.length; zoneItr++) {
	const zone = activeZones[zoneItr];
    const zoneHigh = land_points_onto_series([zone.start], [zone.high], time, 'ge');
    const zoneLow = land_points_onto_series([zone.start], [zone.low], time, 'ge');
    const zoneMid = land_points_onto_series([zone.start], [zone.mid], time, 'ge');
    
    const interpolatedHigh = interpolate_sparse_series(zoneHigh, 'constant');
    const interpolatedLow = interpolate_sparse_series(zoneLow, 'constant');
    const interpolatedMid = interpolate_sparse_series(zoneMid, 'constant');

	const zoneNamePrefix = `Zone ${zoneItr + 1}`
    
    fill(
        paint(interpolatedHigh, { style: 'line', name:`${zoneNamePrefix} High`, color: zoneColor, ignoreWhenScaling: true, hideInLegend: true }),
        paint(interpolatedLow, { style: 'line', name:`${zoneNamePrefix} Low`, color: zoneColor, ignoreWhenScaling: true, hideInLegend: true }),
        zoneColor,
		0.2,
		`${zoneNamePrefix} Fill`
    );
    
    paint(interpolatedMid, { style: 'dotted', name:`${zoneNamePrefix} Mid`, color: midlineColor, linewidth: 1, ignoreWhenScaling: true, hideInLegend: true });
}

for (let i = activeZones.length + 1; i <= maxZones; i++) {
	const zoneNamePrefix = `Zone ${i}`

    fill(
        paint(series_of(null), { style: 'line', name:`${zoneNamePrefix} High`, color: zoneColor, hidden: true, ignoreWhenScaling: true, hideInLegend: true }),
        paint(series_of(null), { style: 'line', name:`${zoneNamePrefix} Low`, color: zoneColor, hidden: true, ignoreWhenScaling: true, hideInLegend: true }),
		0.2,
        zoneColor,
		`${zoneNamePrefix} Fill`
    );

    paint(series_of(null), { style: 'dotted', name:`${zoneNamePrefix} Mid`, color: midlineColor, linewidth: 1, ignoreWhenScaling: true, hideInLegend: true });
}
</code>