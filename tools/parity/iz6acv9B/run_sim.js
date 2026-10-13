// node run_sim.js <foresight csv>  -> the simulation's trades as JSON (default inputs of the Pine script)
const fs = require("fs");
const { vmcSimulate } = require("./sim.js");
const rows = fs.readFileSync(process.argv[2], "utf8").trim().split("\n").slice(1).map((l) => l.split(","));
const O = rows.map((r) => +r[3]), H = rows.map((r) => +r[4]), L = rows.map((r) => +r[5]), C = rows.map((r) => +r[6]);
const P = { chLen: 9, avgLen: 27, maLen: 3, minSwing: 10, trendFilter: false, emaLen: 200,
            tp1: 50, tp2: 50, tp3: 50, tp4: 50, tp5: 50, enableSL: true, slType: "ATR", atrLen: 14, atrMult: 2, fixedPct: 1,
            capital: 100000, pct: 2, tick: +rows[0][9], roundAll: false };
const out = vmcSimulate(O, H, L, C, P);
process.stdout.write(JSON.stringify(out.trades));
