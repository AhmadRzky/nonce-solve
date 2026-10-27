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
fs.writeFileSync("inst.json", JSON.stringify({ variables: 1536, clauses }));
console.log("converted:", clauses.length, "clauses");
