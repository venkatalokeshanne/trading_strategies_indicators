<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Liquidity Zone Scanner');

// Import tinycolor library
const tinycolor = library('tinycolor2');

// 1. Find significant highs and lows (fractals)
const myHighs = fractal_high(high, 5);
const myLows = fractal_low(low, 5);

// 2. Cluster these price levels within a certain percentage band
const myClusterTolerance = input.number('Cluster Tolerance', 0.005, { min: 0.001, max: 0.1, step: 0.001 });

// Helper function to cluster values
const cluster_values = (series, tolerance) => {
    const clusters = [];
    const nonNullValues = indexed_points_of(series);
    for (const point of nonNullValues) {
        let foundCluster = false;
        for (const cluster of clusters) {
            if (Math.abs(point.value - cluster.price) / cluster.price <= tolerance) {
                cluster.count++;
                cluster.price = (cluster.price * cluster.count + point.value) / (cluster.count + 1);
                foundCluster = true;
                break;
            }
        }
        if (!foundCluster) {
            clusters.push({ price: point.value, count: 1, firstIndex: point.candleIndex });
        }
    }
    return clusters;
};

const myHighLevels = cluster_values(myHighs, myClusterTolerance);
const myLowLevels = cluster_values(myLows, myClusterTolerance);

// 3. Find High-Volume Nodes (simplified approach)
const myVolumeThreshold = input.number('Volume Threshold', 1.5, { min: 1, max: 5, step: 0.1 });
const myVolumePeriod = input.number('Volume Period', 20, { min: 5, max: 100 });
const myAvgVolume = sma(volume, myVolumePeriod);
const myHighVolume = for_every(volume, myAvgVolume, (v, avg) => v > avg * myVolumeThreshold ? 1 : 0);
const myHvnLevels = cluster_values(for_every(myHighVolume, close, (hv, c) => hv ? c : null), myClusterTolerance);

// 4. Combine all significant levels
const myAllKeyLevels = [...myHighLevels, ...myLowLevels, ...myHvnLevels];

// 5. Paint - Project these levels forward as zones
for (const myLevel of myAllKeyLevels) {
    const myStrength = Math.min(myLevel.count / 5, 1); // Normalize strength
    const myColor = tinycolor(myStrength > 0.6 ? 'red' : 'blue').setAlpha(0.2 + myStrength * 0.3).toRgbString();
    
    paint(
        horizontal_line(myLevel.price, myLevel.firstIndex),
        {
            color: myColor,
            linewidth: 2,
            name: `Zone ~${myLevel.price.toFixed(2)}`,
            style: 'dotted'
        }
    );
}
</code>