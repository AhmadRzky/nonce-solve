// Chip404 on-chain state + fleet target helper.
// Reads weightNow, targetNow, totalMinted, mintedBy(wallet), trialOpen, paused and prints
// the hex targets for the current weight (loose) and weight+1 (strict = fleet primary).
// Uses ethers when available (local ops box); falls back to raw JSON-RPC fetch.
const RPCS = ["https://bsc-dataseed.binance.org", "https://bsc-dataseed1.defibit.io", "https://bsc-dataseed1.ninicoin.io", "https://bsc-dataseed2.defibit.io"];
const CONTRACT = "0xAB6b18C626daaDd1ff7Cc45F402141153a5a9759";
const WALLET = "0x36BfCce478a860F316c9F6b1405D166FD96e513b";
const SEL = { weightNow: "0x0a954472", targetNow: "0x09a9efa7", totalMinted: "0xa2309ff8", mintedBy: "0x3cef28d2", trialOpen: "0x66de08fa", paused: "0x5c975abb" };
const targetHex = (w) => ((1n << BigInt(256 - w)) - 1n).toString(16).padStart(64, "0");
function loadEthers() {
  for (const p of ["ethers", "/home/hatch/workspace/tools/eth/node_modules/ethers", "../tools/eth/node_modules/ethers"]) {
    try { return require(p); } catch (e) { /* try next */ }
  }
  return null;
}
async function viaEthers(ethers) {
  const ABI = ["function weightNow() view returns (uint256)", "function targetNow() view returns (uint256)", "function totalMinted() view returns (uint256)", "function mintedBy(address) view returns (uint256)", "function trialOpen() view returns (bool)", "function paused() view returns (bool)"];
  for (const rpc of RPCS) {
    try {
      const p = new ethers.JsonRpcProvider(rpc, 56, { staticNetwork: true });
      const c = new ethers.Contract(CONTRACT, ABI, p);
      const [w, t, m, mb, open, paused] = await Promise.all([c.weightNow(), c.targetNow(), c.totalMinted(), c.mintedBy(WALLET), c.trialOpen(), c.paused()]);
      return { rpc, w, t, m, mb, open, paused };
    } catch (e) { console.error("RPC FAIL", rpc, String(e.message || e).slice(0, 160)); }
  }
  return null;
}
async function callRaw(rpc, data) {
  const r = await fetch(rpc, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to: CONTRACT, data }, "latest"] }) });
  const j = await r.json();
  if (j.error) throw new Error(JSON.stringify(j.error));
  return j.result;
}
async function viaRaw() {
  for (const rpc of RPCS) {
    try {
      const [w, t, m, mb, open, paused] = await Promise.all([
        callRaw(rpc, SEL.weightNow), callRaw(rpc, SEL.targetNow), callRaw(rpc, SEL.totalMinted),
        callRaw(rpc, SEL.mintedBy + "000000000000000000000000" + WALLET.slice(2).toLowerCase()),
        callRaw(rpc, SEL.trialOpen), callRaw(rpc, SEL.paused),
      ]);
      return { rpc, w: BigInt(w), t: BigInt(t), m: BigInt(m), mb: BigInt(mb), open: BigInt(open) === 1n, paused: BigInt(paused) === 1n };
    } catch (e) { console.error("RPC FAIL", rpc, String(e.message || e).slice(0, 160)); }
  }
  return null;
}
(async () => {
  const ethers = loadEthers();
  const res = ethers ? await viaEthers(ethers) : await viaRaw();
  if (!res) { console.error("all RPCs failed"); process.exit(1); }
  const weight = Number(res.w);
  console.log(JSON.stringify({
    rpc: res.rpc, weightNow: weight, targetNow_dec: res.t.toString(), totalMinted: Number(res.m),
    mintedBy: Number(res.mb), trialOpen: !!res.open, paused: !!res.paused,
    loose_target_hex: targetHex(weight), strict_target_hex: targetHex(weight + 1),
  }, null, 2));
})();
