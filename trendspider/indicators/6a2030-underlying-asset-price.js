<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Underlying asset price', 'lower');


// If the current symbol is an option, fetch and paint the underlying asset chart
if (current.root) {
    // current.root contains the underlying symbol for options
    const underlyingData = await request.history(current.root, current.resolution);
    assert(!underlyingData.error, `Error fetching underlying data: ${underlyingData.error}`);
    
    // Land the underlying data onto the current chart's time series
    const underlyingLanded = land_points_onto_series(
        underlyingData.time, 
        underlyingData.close, 
        time, 
        'ge'
    );
    
    // Interpolate to fill gaps
    const underlyingInterpolated = interpolate_sparse_series(underlyingLanded, 'constant');
    
    // Paint as a lower indicator
    paint(underlyingInterpolated, { 
        name: `Underlying`,
        color: 'blue',
        style: 'line'
    });
}
else {
	throw "Only applicable to options";
}</code>