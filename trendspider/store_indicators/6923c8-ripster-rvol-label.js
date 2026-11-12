<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Ripster RVol Label');

// Define the volume length input
const volumeLength = input.number('Average Volume Length', 20, { min: 1 });

// Check if the current timeframe is intraday (numeric resolution means minutes)
const isIntradayTimeframe = !isNaN(parseInt(current.resolution));

// For intraday timeframes, fetch daily data to compute daily-based RVol
let myAvgVolume;
let myRvol;
let myLabelString;
let myBackgroundColor;

if (isIntradayTimeframe) {
    // Fetch daily data for the current ticker
    const dailyData = await request.history(current.ticker, 'D');
    assert(!dailyData.error, `Error fetching daily data: ${dailyData.error}`);
    
    // Calculate average volume on daily data
    const dailyAvgVolume = sma(shift(dailyData.volume, 1), volumeLength);
    
    // Calculate RVol on daily data
    const dailyRvol = div(mult(dailyData.volume, 100), dailyAvgVolume);
    
    // Get the latest daily values
    const latestDailyVolume = dailyData.volume[dailyData.volume.length - 1];
    const latestDailyAvgVolume = dailyAvgVolume[dailyAvgVolume.length - 1];
    const latestDailyRvol = dailyRvol[dailyRvol.length - 1];
    
    // Format volume helper function
    const formatVolume = (vol) => {
        if (vol >= 1000000) {
            return (vol / 1000000).toFixed(2) + ' M';
        } else if (vol >= 1000) {
            return (vol / 1000).toFixed(2) + 'k';
        } else {
            return vol.toFixed(2);
        }
    };
    
    // Create label string from latest daily values
    const formattedVol = formatVolume(latestDailyVolume);
    const formattedAvg = formatVolume(latestDailyAvgVolume);
    const roundedRvol = Math.round(latestDailyRvol).toString().padStart(3);
    const labelText = `Vol: ${formattedVol}    |    Avg Vol: ${formattedAvg}    |    RVol: ${roundedRvol}%`;
    
    // Determine background color based on RVol
    const backgroundColor = latestDailyRvol <= 20 ? '#FF9999' : '#99FF99';
    
    // Paint the overlay for intraday (fixed position from 'top_center' to 'top_right')
    paint_overlay('RVol Table', { position: 'top_right', order: 'above_all' }, {
        rows: [{
            cells: [{
                text: labelText,
                background: backgroundColor,
                padding: 5,
                fontFamily: 'Arial, sans-serif',
                color: 'black',
                borderRadius: '5px',
                whiteSpace: 'pre',
                fontWeight: 'bold',
                fontSize: '14px'
            }]
        }]
    });
} else {
    // For daily, weekly, or monthly timeframes, use the original logic
    const isApplicableTimeframe = ['D', 'W', 'M'].includes(current.resolution);
    
    if (isApplicableTimeframe) {
        myAvgVolume = sma(shift(volume, 1), volumeLength);
        myRvol = div(mult(volume, 100), myAvgVolume);
        
        const formatVolume = (vol) => {
            if (vol >= 1000000) {
                return (vol / 1000000).toFixed(2) + ' M';
            } else if (vol >= 1000) {
                return (vol / 1000).toFixed(2) + 'k';
            } else {
                return vol.toFixed(2);
            }
        };
        
        myLabelString = for_every(volume, myAvgVolume, myRvol, (_v, _a, _r) => {
            const formattedVol = formatVolume(_v);
            const formattedAvg = formatVolume(_a);
            const roundedRvol = Math.round(_r).toString().padStart(3);
            return `Vol: ${formattedVol}    |    Avg Vol: ${formattedAvg}    |    RVol: ${roundedRvol}%`;
        });
        
        myBackgroundColor = for_every(myRvol, _r => _r <= 20 ? '#FF9999' : '#99FF99');
        
        paint_overlay('RVol Table', { position: 'top_right', order: 'above_all' }, {
            rows: [{
                cells: [{
                    text: myLabelString[myLabelString.length - 1],
                    background: myBackgroundColor[myBackgroundColor.length - 1],
                    padding: 5,
                    fontFamily: 'Arial, sans-serif',
                    color: 'black',
                    borderRadius: '5px',
                    whiteSpace: 'pre',
                    fontWeight: 'bold',
                    fontSize: '14px'
                }]
            }]
        });
    } else {
        paint_overlay('RVol Table', { position: 'top_right', order: 'above_all' }, {
            rows: []
        });
    }
}</code>