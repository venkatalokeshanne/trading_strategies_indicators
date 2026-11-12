<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Put/Call Ratio');

// Fetch options grid data for both Puts and Calls
// We request 6 strikes around current price to get a good sample
const optionsData = await request.options_data_for_all_expirations(
    current.ticker, 
    30, 
    ['oi'], 
    'all'
);

assert(!optionsData.error, `Error fetching options data: ${optionsData.error}`);

// Calculate total OI for Calls and Puts across all expirations and strikes
let myTotalCallsOI = 0;
let myTotalPutsOI = 0;

// Iterate through all expirations
for (const myExpiration in optionsData.resultByExpiration) {
    const myStrikesData = optionsData.resultByExpiration[myExpiration];
    
    // Iterate through all strikes in this expiration
    for (const myStrike in myStrikesData) {
        const myStrikeData = myStrikesData[myStrike];
        
        // Add Calls OI if it exists
        if (myStrikeData.C && myStrikeData.C.oi) {
            myTotalCallsOI += myStrikeData.C.oi;
        }
        
        // Add Puts OI if it exists
        if (myStrikeData.P && myStrikeData.P.oi) {
            myTotalPutsOI += myStrikeData.P.oi;
        }
    }
}

const myTotal = myTotalCallsOI + myTotalPutsOI;
const myCallsPercent = myTotal > 0 ? ((myTotalCallsOI / myTotal) * 100).toFixed(1) : 0;
const myPutsPercent = myTotal > 0 ? ((myTotalPutsOI / myTotal) * 100).toFixed(1) : 0;

// Calculate Put/Call ratio
const myPutCallRatio = myTotalCallsOI > 0 ? (myTotalPutsOI / myTotalCallsOI).toFixed(2) : 0;

// Paint the overlay with pie chart
paint_overlay('Chart', { position: 'bottom_left', offset_x: 10, offset_y: 0 }, {
    rows: [, {
        cells: [{
        	textAlign: 'center',
            text: 'Put/Call Ratio',
            paddingBottom: 7,
            color: 'var(--text-color)'
        }]
    }, {
        cells: [{
            chart: {
                width: '80px',
                height: '80px',
                type: 'doughnut',
                options: {
                    plugins: {
                        legend: {
                            display: false,
                            position: 'inset'
                        },
                        datalabels: {
                            display: true
                        }
                    },
                    cutout: '70%'
                },
                data: {
                    labels: [`Calls ${myCallsPercent}%`, `Puts ${myPutsPercent}%`],
                    datasets: [{
                        data: [myTotalCallsOI, myTotalPutsOI],
                        backgroundColor: ['#12d962', '#ff4444'],
                        borderColor: ['#0fa84d', '#cc0000'],
                        borderWidth: 2,
                        datalabels: {
                            display: false
                        }
                    }]
                }
            }
        }]
    }, {
        cells: [{
        	position: 'relative',
        	textAlign: 'center',
        	top: -55,
        	fontSize: 20,
        	fontWeight: 'bold',
            text: myPutCallRatio,
            color: 'var(--text-color)'
        }]
    }]
});</code>