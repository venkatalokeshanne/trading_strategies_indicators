<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Has Options - Fixed');

// Use TrendSpider's built-in options data instead of external API
let hasOptions = false;
let optionsCount = 0;
let errorMessage = '';

try {
    // Get options data from TrendSpider (same as successful GEX indicator)
    const optionsData = await request.unusual_options(current.ticker);
    
    // Check if we have valid options data
    if (optionsData && Array.isArray(optionsData) && optionsData.length > 0) {
        // Filter for valid options (same criteria as GEX indicator)
        const validOptions = optionsData.filter(option => 
            option.strike && 
            option.size && 
            option.type && 
            (option.type === 'CALL' || option.type === 'PUT')
        );
        
        hasOptions = validOptions.length > 0;
        optionsCount = validOptions.length;
    } else {
        hasOptions = false;
        optionsCount = 0;
    }
    
} catch (error) {
    hasOptions = false;
    errorMessage = String(error);
}

// Create the indicator overlay
paint_overlay('HasOptions', { 
    position: 'bottom_right',
	offset_x: -50,
    offset_y: 0, 
    order: 'above_all' 
}, {
    background: 'var(--background-color)',
    border: hasOptions ? '1px solid #00FF00' : '1px solid #FF0000',
    borderRadius: '4px',
    rows: [{
        cells: [{
            text: errorMessage ? 
                `${current.ticker} Options: Error checking` :
                `${current.ticker} Options: ${hasOptions ? `Yes🟢 (${optionsCount})` : 'No🔴'}`,
            color: errorMessage ? 'yellow' : (hasOptions ? 'lightgreen' : 'pink'),
            fontWeight: 'bold',
            padding: '8px'
        }]
    }]
});

// Register a signal when options are available
register_signal(series_of(!!errorMessage), 'Has Options Error');
register_signal(series_of(errorMessage ? false : hasOptions), 'Has Options');</code>