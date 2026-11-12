<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Dollar Volume', 'lower');

// Get the dollar volume by multiplying close price by volume
const myDollarVolume = mult(close, volume);

// Paint the dollar volume as columns
paint(myDollarVolume, { name: 'Dollar Volume', color: 'green', style: 'column' });</code>