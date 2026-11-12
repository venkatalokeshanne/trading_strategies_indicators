<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Ehlers Decycler', 'price', { shortName: 'Decycler', decimals: 2 });

// Inputs
const length = input.number('Length', 60, { min: 1 , max: 10000});
const src = input.select('Source', 'close', ['open', 'high', 'low', 'close']);
const clr_mono = input.color('Mono Color', 'blue');
const clr_up = input.color('Up Color', 'green');
const clr_dn = input.color('Down Color', 'red');
const smart_clr_ON = input.boolean('Colorize', true);
const line_width = input.number('Line Width', 2, { min: 1, max: 20 });

// Function to calculate the Decycler
function Decycler(src, length) {
    const PIx2_Length = Math.PI * 2 / length;
    const cos = Math.cos(PIx2_Length);
    let alpha = cos !== 0 ? (cos + Math.sin(PIx2_Length) - 1) / cos : 0;

    let decycler = series_of(null);
    for (let i = 1; i < src.length; i++) {
        if (i === 1) {
            decycler[i] = alpha / 2 * (src[i] + src[i - 1]);
        } else {
            decycler[i] = alpha / 2 * (src[i] + src[i - 1]) + (1 - alpha) * decycler[i - 1];
        }
    }
    return decycler;
}

// Function to determine color based on trend
function MA_Smart_Color(ma, smart_clr_ON, color_up, color_dn, clr) {
    let clr_ma = series_of(null);
    for (let i = 1; i < ma.length; i++) {
        if (!smart_clr_ON) {
            clr_ma[i] = clr;
        } else if (ma[i] > ma[i - 1]) {
            clr_ma[i] = color_up;
        } else if (ma[i] < ma[i - 1]) {
            clr_ma[i] = color_dn;
        } else {
            clr_ma[i] = clr_ma[i - 1];
        }
    }
    return clr_ma;
}

// Get the selected price series
const priceSeries = {
    open: open,
    high: high,
    low: low,
    close: close
}[src];

// Calculate the Decycler
const ma = Decycler(priceSeries, length);
const clr_ma = MA_Smart_Color(ma, smart_clr_ON, clr_up, clr_dn, clr_mono);

// Plot the Decycler
paint(ma, { name: 'Decycler', color: clr_ma, thickness: line_width });

// Events for alerts
const EVENT_up = for_every(ma, (val, idx) => val > ma[idx - 1] && idx > 0);
const EVENT_dn = for_every(ma, (val, idx) => val < ma[idx - 1] && idx > 0);

// Register signals for alerts
register_signal(EVENT_up, 'Trend up');
register_signal(EVENT_dn, 'Trend down');
</code>