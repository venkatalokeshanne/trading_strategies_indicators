<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Moon Phases', 'price', { shortName: 'Moon Phases' });

const moment = library('moment-timezone');

// Function to calculate moon phase
function getMoonPhase(julianDate) {
    const knownNewMoon = 2451550.1; // Julian date of a known new moon (January 6, 2000, 18:14 UT)
    const synodicMonth = 29.53058867; // Length of a synodic month in days

    const daysSinceNewMoon = julianDate - knownNewMoon;
    const newMoons = Math.floor(daysSinceNewMoon / synodicMonth);
    const phase = daysSinceNewMoon - (newMoons * synodicMonth);

    return phase / synodicMonth;
}

// Convert date to Julian date with time precision
function toJulianDate(timestamp) {
    // Convert timestamp to UT using moment-timezone
    const date = moment.tz(timestamp * 1000, "UTC");

    const year = date.year();
    const month = date.month() + 1; // Moment months are 0-11, Julian needs 1-12
    const day = date.date();
    const hours = date.hours();
    const minutes = date.minutes();
    const seconds = date.seconds();

    // Simplified Julian date calculation with time adjustment
    let a = Math.floor((14 - month) / 12);
    let y = year + 4800 - a;
    let m = month + 12 * a - 3;

    let jd = day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;

    // Add the fractional part of the day
    const dayFraction = (hours + (minutes / 60) + (seconds / 3600)) / 24;
    return jd + dayFraction;
}

// Paint moon phase symbols based on moon phase
const symbols = series_of(null);

const newMoonSignal = series_of(false);
const firstQuarterSignal = series_of(false);
const fullMoonSignal = series_of(false);
const lastQuarterSignal = series_of(false);

let previousPhase = null;

for (let i = 0; i < time.length; i++) {
    const julianDate = toJulianDate(time[i]);
    const moonPhase = getMoonPhase(julianDate);

    if (previousPhase === null || Math.floor(previousPhase * 8) !== Math.floor(moonPhase * 8)) {
        let symbol;

        // Define all eight moon phases with tighter ranges for key phases
        if (moonPhase < 0.025 || moonPhase >= 0.975) {
            symbol = '🌑'; // New moon
            newMoonSignal[i] = true;
        } else if (moonPhase >= 0.025 && moonPhase < 0.225) {
            symbol = '🌒'; // Waxing crescent moon
        } else if (moonPhase >= 0.225 && moonPhase < 0.275) {
            symbol = '🌓'; // First quarter moon
            firstQuarterSignal[i] = true;
        } else if (moonPhase >= 0.275 && moonPhase < 0.475) {
            symbol = '🌔'; // Waxing gibbous moon
        } else if (moonPhase >= 0.475 && moonPhase < 0.525) {
            symbol = '🌕'; // Full moon
            fullMoonSignal[i] = true;
        } else if (moonPhase >= 0.525 && moonPhase < 0.725) {
            symbol = '🌖'; // Waning gibbous moon
        } else if (moonPhase >= 0.725 && moonPhase < 0.775) {
            symbol = '🌗'; // Last quarter moon
            lastQuarterSignal[i] = true;
        } else if (moonPhase >= 0.775 && moonPhase < 0.975) {
            symbol = '🌘'; // Waning crescent moon
        }

        symbols[i] = symbol;
    }

    previousPhase = moonPhase;
}

// Paint the moon phase symbols on the chart
paint(symbols, {
    name: 'Moon Phase',
    style: 'labels_above',
    color: 'white',
    thickness: 1
});

// Register signals for potential use in alerts or strategies
register_signal(newMoonSignal, 'New Moon');
register_signal(firstQuarterSignal, 'First Quarter Moon');
register_signal(fullMoonSignal, 'Full Moon');
register_signal(lastQuarterSignal, 'Last Quarter Moon');</code>