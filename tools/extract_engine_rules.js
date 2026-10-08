// Capture TrendSpider's script-validation rules straight from its own engine, so the lint
// enforces exactly what TrendSpider enforces instead of a hand-written guess.
//
// It loads the captured engine bundle (local only, never committed), records the scope
// object `F` at the moment TrendSpider validates a script — Object.keys(F) IS the
// reserved-identifier set — and writes the rules to tools/trendspider_rules.json.
// That output is a list of API names and limits: facts about the interface, not engine
// code, so it is committed and the lint works on machines without the bundle.
//
// usage: node tools/extract_engine_rules.js        (TS_BUNDLE overrides the bundle path)

const fs = require('fs'), path = require('path'), vm = require('vm');
const BUNDLE = process.env.TS_BUNDLE ||
    'C:/Users/annev/Downloads/trendspider-automation/data/extraction/runtime_bundle/00_pretty.js';

let src = fs.readFileSync(BUNDLE, 'utf8');
const patches = [
    // expose the webpack loader (same hook the parent project's load_engine.js uses)
    ['  const r = self.assert = (e, t) => {', '  globalThis.__wpreq = n;\n  const r = self.assert = (e, t) => {'],
    // record the scope object right before validation
    ['const G = T.validateScriptSyntax(e, F);', 'globalThis.__scope = Object.keys(F); const G = T.validateScriptSyntax(e, F);'],
];
for (const [find, repl] of patches) {
    if (!src.includes(find)) { console.error(`bundle layout changed: marker not found: ${find.slice(0, 60)}`); process.exit(2); }
    src = src.replace(find, repl);
}

// The validator's literal sets, read from the same source so they can never drift.
const grab = re => { const m = src.match(re); return m ? m[1] : null; };
const parseList = s => (s ? s.split(',').map(x => x.trim().replace(/^"|"$/g, '')).filter(x => x && !x.startsWith('...')) : []);
const bannedKeywords = parseList(grab(/const r = new Set\(\[([^\]]*)\]\),\s*a = new Set/));
const bannedNamesExtra = parseList(grab(/a = new Set\(\[\.\.\.w, ([^\]]*)\]\)/));
const bannedNamesW = parseList(grab(/w = \[([^\]]*)\],\s*T = /));
const declTokens = parseList(grab(/const s = \[([^\]]*)\],\s*o = `/));
const ecma = grab(/ecmaVersion: (\d{4})/);

const sandbox = {
    console, setTimeout, clearTimeout, setInterval, clearInterval, setImmediate, Promise, URL,
    TextEncoder, TextDecoder, queueMicrotask, structuredClone, addEventListener() {}, postMessage() {}, performance,
};
sandbox.self = sandbox; sandbox.globalThis = sandbox; sandbox.window = undefined;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: 'ts_engine.js' });

(async () => {
    const eng = sandbox.__wpreq(77);
    const t0 = 1704067200;
    const candles = Array.from({ length: 50 }, (_, i) => [(t0 + i * 86400) * 1000, 100 + i, 101 + i, 99 + i, 100.5 + i, 1e6]);
    const session = { identifier: 'us_regular', timezone: 'America/New_York', start: { hours: 9, minutes: 30 },
        end: { hours: 16, minutes: 0 }, lengthMinutes: 390, marketDays: [1, 2, 3, 4, 5] };
    await eng.calculateScript("describe_indicator('probe', 'lower'); paint(close, { name: 'c' });", {}, candles, {
        symbolInfo: { ticker: 'AAPL', decimals: 2, type: 'stock', hasVolume: true, session, extendedSession: session,
            preMarketSession: session, postMarketSession: session, root: 'AAPL' },
        resolution: 'D', externalCallsHandlers: {}, neverAppendTime: false, is_ext_hours: false,
    });
    const reserved = (sandbox.__scope || []).slice().sort();
    if (!reserved.length) { console.error('scope not captured — validation did not run'); process.exit(3); }
    const rules = {
        source: 'TrendSpider client scripting engine (captured bundle), validateScriptSyntax',
        extracted: new Date().toISOString().slice(0, 10),
        ecmaVersion: Number(ecma),
        bannedKeywords,
        bannedNames: [...new Set([...bannedNamesW, ...bannedNamesExtra])].sort(),
        declarationTokens: declTokens,
        reservedIdentifiers: reserved,
        notes: [
            'A reserved identifier raises an error only when it is the token directly after a ' +
            'declaration token, or the single name directly before "=>". ' +
            '`const [atr] = ...`, `let a, atr` and `(atr) => ...` are NOT rejected by this check.',
            'The script is wrapped as (async() => { ... })() before parsing, so top-level await works.',
        ],
    };
    const out = path.join(__dirname, 'trendspider_rules.json');
    fs.writeFileSync(out, JSON.stringify(rules, null, 1) + '\n');
    console.log(`ecmaVersion ${rules.ecmaVersion}; banned keywords: ${bannedKeywords.join(', ')}`);
    console.log(`banned names: ${rules.bannedNames.length}; declaration tokens: ${declTokens.join(', ')}`);
    console.log(`reserved identifiers: ${reserved.length}`);
    console.log(`written: ${out}`);
})().catch(e => { console.error(e); process.exit(1); });
