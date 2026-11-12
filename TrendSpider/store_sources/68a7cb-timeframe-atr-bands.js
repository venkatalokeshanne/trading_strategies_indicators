<code x-ref="code" class="hljs" data-clipboard-text>// ░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓████████▓▒░       ░▒▓███████▓▒░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓███████▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓██████▓▒░         ░▒▓██████▓▒░░▒▓██████▓▒░ ░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░ ░▒▓██████▓▒░  
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓████████▓▒░      ░▒▓███████▓▒░░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░                                                                                                                                                                      

describe_indicator('Timeframe ATR Bands', { decimals: 2, warmup: '500' });

// inputs
const timeframeInput = input.select('Timeframe', 'W', constants.time_frames);
const atrLengthInput = input.number('ATR Length', 52, { min: 1, max: 500 });

// logic
// Fetch data from higher timeframe
const timeframeData = await request.history(current.ticker, timeframeInput);
assert(!timeframeData.error, `Error fetching data: ${timeframeData.error}`);

// Calculate ATR on higher timeframe
const avgTrueRange = atr(timeframeData.high, timeframeData.low, timeframeData.close, atrLengthInput);

// Land ATR onto current timeframe
const atrLanded = land_points_onto_series(timeframeData.time, avgTrueRange, time, 'ge');
const atrInterpolated = interpolate_sparse_series(atrLanded, 'constant');

// Initialize series for our lines
const midLine = series_of(null);
const highLine = series_of(null);
const lowLine = series_of(null);
const highExtension = series_of(null);
const lowExtension = series_of(null);

// Identify the start of each higher timeframe period
const periodsStart = [];
for (let i = 0; i < time.length; i++) {
    if (i === 0 || bar_at(time[i], timeframeInput).session !== bar_at(time[i-1], timeframeInput).session) {
        periodsStart.push(i);
    }
}

// Calculate lines
for (let i = 0; i < periodsStart.length; i++) {
    const startIndex = periodsStart[i];
    const endIndex = i < periodsStart.length - 1 ? periodsStart[i+1] : time.length;
    const periodOpen = open[startIndex];
    const periodAtr = atrInterpolated[startIndex];
    
    for (let j = startIndex; j < endIndex; j++) {
        midLine[j] = periodOpen;
        highLine[j] = periodOpen + periodAtr / 2;
        lowLine[j] = periodOpen - periodAtr / 2;
        highExtension[j] = periodOpen + periodAtr;
        lowExtension[j] = periodOpen - periodAtr;
    }
}

// plots
const midLinePainted = paint(midLine, { color: 'orange', name: 'Mid', style: 'ladder' });
const highLinePainted = paint(highLine, { color: 'red', name: 'High', style: 'dotted' });
const lowLinePainted = paint(lowLine, { color: 'green', name: 'Low', style: 'dotted' });
const highExtensionPainted = paint(highExtension, { color: 'red', name: 'High Extension', style: 'ladder' });
const lowExtensionPainted = paint(lowExtension, { color: 'green', name: 'Low Extension', style: 'ladder' });

fill(highLinePainted, highExtensionPainted, 'red', 0.05, 'High Fill');
fill(lowLinePainted, lowExtensionPainted, 'green', 0.05, 'Low Fill');</code>