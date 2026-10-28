import fs from "node:fs";
const txt = fs.readFileSync(process.argv[2] || "inst.cnf", "utf8");
const clauses = [];
let cur = [];
for (const line of txt.split(/\r?\n/)) {
  const t = line.trim();
  if (!t || t.startsWith("c") || t.startsWith("p") || t.startsWith("%")) continue;
  for (const tok of t.split(/\s+/)) {
    const n = parseInt(tok, 10);
    if (Number.isNaN(n)) continue;
    if (n === 0) { if (cur.length) { clauses.push(cur); cur = []; } }
    else cur.push(n);
  }
}
if (cur.length) clauses.push(cur);
let vars = 0;
const pm = txt.match(/^p\s+cnf\s+(\d+)\s+(\d+)/m);
if (pm) vars = parseInt(pm[1], 10);
if (!vars) for (const c of clauses) for (const l of c) vars = Math.max(vars, Math.abs(l));
fs.writeFileSync("inst.json", JSON.stringify({ variables: vars, clauses }));
console.log("converted:", clauses.length, "clauses");
