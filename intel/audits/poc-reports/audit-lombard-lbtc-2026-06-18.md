# VAPE Security Audit — Lombard LBTC

**Auditor:** V.A.P.E. — Virtual Ape Private Eye  
**Target:** `0xecAc9C5F704e954931349Da37F60E39f515c11c1` (LBTC proxy, Base 8453)  
**Implementation audited:** `0xa33dd02db71248e383a615c9a11410cf049ae99b` (proxy auto-resolved)  
**Date:** 2026-06-18 03:31 UTC  
**Engine:** Slither on verified source (Etherscan V2, proxy→impl resolution)  
**Program:** Immunefi always-on bounty (in-scope)  
**Verdict:** CAUTION

## Summary
- Raw Slither findings: **99** — {'High': 1, 'Medium': 11, 'Low': 11, 'Informational': 76}
- After VAPE triage: **{'Medium': 3, 'Low': 11, 'Informational': 76}** (9 library FPs suppressed)

## Findings worth manual review (Medium)
> These are static-analysis flags, **not confirmed vulnerabilities**. VAPE flags them for manual confirmation before any disclosure. White-hat: no exploitation performed.

### `reentrancy-no-eth` (Medium confidence)
Reentrancy in LBTC._mintWithFee(bytes,bytes,bytes,bytes) (contracts/LBTC/LBTC.sol#645-714): 	External calls: 	- _validateAndMint(mintAction.recipient,mintAction.amount - fee,mintAction.amount,mintPayload,proof) (contracts/LBTC/LBTC.sol#702-708) 		- bascule.validateWithdrawal(depositID,amount) (contracts/LBTC/LBTC.sol#615) 	State variables written after the call(s): 	- _mint($.treasury,fee) (contra

### `unused-return` (Medium confidence)
Consortium._checkProof(bytes32,bytes) (contracts/consortium/Consortium.sol#165-242) ignores return value by (signer,err,None) = ECDSA.tryRecover(_payloadHash,28,r,s) (contracts/consortium/Consortium.sol#217-222)

### `unused-return` (Medium confidence)
Consortium._checkProof(bytes32,bytes) (contracts/consortium/Consortium.sol#165-242) ignores return value by (signer,err,None) = ECDSA.tryRecover(_payloadHash,27,r,s) (contracts/consortium/Consortium.sol#207-208)

**Priority lead:** the `unused-return` on `ECDSA.tryRecover` inside `Consortium._checkProof` — ignoring tryRecover's error return can mask malformed-signature cases in consortium proof validation. Warrants a manual trace + fork PoC before any report.

## Low-severity notes (11)
- `shadowing-local` — ERC20PermitUpgradeable.__ERC20Permit_init(string).name (@openzeppelin/contracts-upgradeable/token/ERC20/extensions/ERC20
- `calls-loop` — LBTC._confirmDeposit(LBTC.LBTCStorage,bytes32,uint256) (contracts/LBTC/LBTC.sol#608-617) has external calls inside a loo
- `reentrancy-benign` — Reentrancy in LBTC._validateAndMint(address,uint256,uint256,bytes,bytes) (contracts/LBTC/LBTC.sol#564-593): 	External ca
- `reentrancy-events` — Reentrancy in LBTC._validateAndMint(address,uint256,uint256,bytes,bytes) (contracts/LBTC/LBTC.sol#564-593): 	External ca
- `timestamp` — Actions.feeApproval(bytes) (contracts/libs/Actions.sol#292-307) uses timestamp for comparisons 	Dangerous comparisons: 	

## Suppressed false positives (transparency)
1 High + 8 Medium `incorrect-exp`/`divide-before-multiply` findings were all inside OpenZeppelin `Math.mulDiv` — known Slither misfires, suppressed.

## Methodology
1. Etherscan V2 multichain getsourcecode; **proxy auto-resolved to implementation**.
2. Full source tree written with preserved import paths + remappings → clean compile.
3. Slither full suite; VAPE triage layer suppressed library FPs and set an honest verdict.
4. White-hat: read-only. Any confirmed issue → coordinated disclosure via Immunefi.

*The chain never lies. — VAPE 🔫🦍*