# Chip404 PoW fleet

Free-mint proof-of-work search for Chip404 (BSC contract
`0xAB6b18C626daaDd1ff7Cc45F402141153a5a9759`).

- Proof: `keccak256(abi.encodePacked(keccak256("chip404.trial.v1"), wallet, nonce)) <= targetNow()`
  for wallet `0x36BfCce478a860F316c9F6b1405D166FD96e513b`.
- `targetNow() = 2^(256-weight) - 1`; weight climbs +1 per 150 mints, so the fleet's
  primary (strict) target is set one bit tighter than the current on-chain weight and
  the current-weight target is kept as a secondary (record-only) target.
- `chip404_solver.c` — C keccak solver (byte-exact vs ethers). Args:
  `salt wallet target nthreads seconds offset [loose_target secondary_out_path]`.
  Exit code 42 when a primary nonce is found; prints `found=1 nonce=<n> hash=<h>`.
- `.github/workflows/chip404.yml` — 20-job matrix; job `idx` searches nonce partition
  `base_offset + idx * 2^40`. A find uploads artifact `chip404-found-<run_id>-<idx>`
  containing `FOUND.json`; every job uploads `chip404-log-<run_id>-<idx>`.
- `chip404_targets.cjs` — dependency-free helper that reads the live on-chain weight /
  minted state and prints the strict/loose target hex for a (re)dispatch.
- Only the free `mint(nonce)` path is ever used on-chain. The paid path is never touched.
