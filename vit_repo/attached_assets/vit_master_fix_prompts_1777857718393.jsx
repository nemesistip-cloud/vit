import { useState } from "react";

// ─── ALL GAPS DATA ────────────────────────────────────────────────
const GAPS = [
  // ══ CRITICAL ══
  {
    id:"G01", sev:"CRITICAL", cat:"Security",
    title:"WebSocket token validated but frontend never sends it",
    location:"frontend/src/lib/websocket.ts L44 + notification-bell.tsx",
    status:"Backend fixed, frontend broken",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: The backend WebSocket at /api/notifications/ws/{user_id}?token=<jwt> now validates the token. But frontend/src/lib/websocket.ts constructs the URL WITHOUT appending the JWT. Result: every connection is rejected with code 4001.

FIX in frontend/src/lib/websocket.ts:
1. Import getToken from ../lib/auth
2. When building the wsUrl, append: + '?token=' + (getToken() ?? '')
3. On 4001 close code, clear auth and redirect to /auth instead of retrying

FIX in frontend/src/components/notification-bell.tsx:
- Confirm it uses the shared websocket.ts singleton (not its own fetch loop)
- Remove any polling fallback — WS is now the only channel

TEST: Open browser DevTools → Network → WS tab. After login you should see:
  wss://your-app.repl.co/api/notifications/ws/1?token=eyJ...
  Server sends: {"action":"connected","unread_count":N}
`
  },
  {
    id:"G02", sev:"CRITICAL", cat:"Infrastructure",
    title:"Redis not wired — rate limits reset on every restart",
    location:"app/api/middleware/rate_limit.py — uses in-memory deque only",
    status:"No REDIS_URL configured, no sliding window",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: rate_limit.py uses an in-memory defaultdict of deques. No Redis. Every Replit restart resets all rate limit buckets. Multi-worker deploys share no state.

STEP 1 — Add to requirements.txt (deduplicated): redis==5.2.1

STEP 2 — Update app/api/middleware/rate_limit.py:
\`\`\`python
import os, time, redis.asyncio as aioredis

_redis_client = None

async def _get_redis():
    global _redis_client
    if _redis_client is None:
        url = os.getenv("REDIS_URL", "")
        if url:
            _redis_client = await aioredis.from_url(url, decode_responses=True)
    return _redis_client

# In dispatch() replace the deque block with:
r = await _get_redis()
if r:
    key = f"rl:{identifier}:{window_seconds}"
    now = time.time()
    async with r.pipeline(transaction=True) as pipe:
        await pipe.zremrangebyscore(key, 0, now - window_seconds)
        await pipe.zadd(key, {str(now) + "_" + str(id(now)): now})
        await pipe.zcard(key)
        await pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()
    count = results[2]
else:
    # fallback: existing in-memory deque (dev only)
    ...
\`\`\`

STEP 3 — Add to Replit Secrets:  REDIS_URL = redis://default:password@host:port

VERIFY: After 2 restarts, rate limit counters persist. GET /health shows redis: "connected".`
  },
  {
    id:"G03", sev:"CRITICAL", cat:"Payments",
    title:"Stripe webhook never validates signature — revenue not credited",
    location:"app/modules/wallet/webhooks.py L216+ — stripe section",
    status:"Route exists, STRIPE_WEBHOOK_SECRET not enforced in all paths",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: The Stripe webhook handler at /webhooks/stripe exists but the signature check silently passes when STRIPE_WEBHOOK_SECRET is empty. Payments processed in test mode are credited; in production the secret is not set so real payments are dropped or accepted without verification.

FIX app/modules/wallet/webhooks.py — Stripe handler:
\`\`\`python
import stripe, os
from fastapi import Request, HTTPException

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    if not secret:
        raise HTTPException(503, "Stripe webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid Stripe signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"].get("user_id", 0))
        plan = session["metadata"].get("plan", "pro")
        amount = Decimal(str(session["amount_total"])) / 100
        # credit wallet + activate subscription
        svc = WalletService(db)
        await svc.credit(user_id, "USD", amount, "stripe_checkout", session["id"])
        await activate_subscription(db, user_id, plan, session["id"])
    
    elif event["type"] == "customer.subscription.deleted":
        customer_id = event["data"]["object"]["customer"]
        await deactivate_subscription_by_stripe_customer(db, customer_id)
    
    return {"status": "ok"}
\`\`\`

REQUIRED Replit Secrets:
- STRIPE_SECRET_KEY = sk_live_...
- STRIPE_WEBHOOK_SECRET = whsec_...

In Stripe Dashboard → Webhooks → Add endpoint:
URL: https://your-app.repl.co/webhooks/stripe
Events: checkout.session.completed, customer.subscription.deleted, invoice.payment_failed`
  },
  // ══ HIGH ══
  {
    id:"G04", sev:"HIGH", cat:"Auth",
    title:"Email verification tokens still in-memory dict (multi-worker broken)",
    location:"app/auth/verification.py L31–32 _verify_tokens, _reset_tokens",
    status:"Dict-based, wiped on restart, broken in multi-worker",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: _verify_tokens and _reset_tokens are process-local Python dicts. On Replit with 2+ workers, a token issued by worker-A is invisible to worker-B. Every restart invalidates all pending tokens.

FIX — Migration (add to alembic/versions/):
\`\`\`python
def upgrade():
    op.create_table('email_tokens',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('token_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('purpose', sa.String(20), nullable=False),  # 'verify' | 'reset'
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_email_tokens_hash', 'email_tokens', ['token_hash'])
\`\`\`

FIX — app/auth/verification.py:
\`\`\`python
import hashlib
from app.db.models import EmailToken  # add this model

def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()

async def store_token(db, user_id, token, purpose, expires_minutes):
    db.add(EmailToken(
        token_hash=_hash_token(token),
        user_id=user_id,
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    ))
    await db.commit()

async def consume_token(db, token, purpose):
    h = _hash_token(token)
    row = (await db.execute(
        select(EmailToken).where(EmailToken.token_hash==h, EmailToken.purpose==purpose, EmailToken.used_at==None)
    )).scalar_one_or_none()
    if not row or row.expires_at < datetime.now(timezone.utc):
        return None
    row.used_at = datetime.now(timezone.utc)
    await db.commit()
    return row.user_id
\`\`\`

Run: alembic upgrade head`
  },
  {
    id:"G05", sev:"HIGH", cat:"Payments",
    title:"Paystack deposit verify endpoint missing — deposits never confirmed",
    location:"app/modules/wallet/routes.py — paystack section",
    status:"Initiate works, verify endpoint missing",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: POST /wallet/deposit/initiate returns a Paystack authorization_url. But there is no verify endpoint. After the user pays and returns to the callback URL, nothing confirms the payment or credits the wallet.

ADD to app/modules/wallet/routes.py:
\`\`\`python
@router.post("/deposit/verify")
async def verify_paystack_deposit(reference: str, current_user=Depends(get_current_user), db=Depends(get_db)):
    import httpx, os
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}"},
            timeout=15,
        )
    data = r.json()
    if data.get("data", {}).get("status") != "success":
        raise HTTPException(400, f"Payment not successful: {data.get('data',{}).get('status')}")
    
    tx_data = data["data"]
    amount_ngn = Decimal(str(tx_data["amount"])) / 100
    meta = tx_data.get("metadata", {})
    
    if int(meta.get("user_id", 0)) != current_user.id:
        raise HTTPException(403, "Reference does not belong to this user")
    
    # idempotency check
    existing = await db.execute(select(WalletTransaction).where(WalletTransaction.external_ref==reference))
    if existing.scalar_one_or_none():
        return {"status": "already_credited", "amount": float(amount_ngn)}
    
    svc = WalletService(db)
    await svc.credit(current_user.id, "NGN", amount_ngn, "paystack_deposit", reference)
    await process_deposit_commission(db, current_user.id, amount_ngn)
    return {"status": "success", "amount": float(amount_ngn), "currency": "NGN"}
\`\`\`

UPDATE frontend/src/pages/payment-callback.tsx:
- On mount, read ?reference= from URL params
- Call apiPost("/api/wallet/deposit/verify", { reference })
- Show success toast + redirect to /wallet`
  },
  {
    id:"G06", sev:"HIGH", cat:"Blockchain",
    title:"No real Base L2 connection — entire blockchain is simulated",
    location:"app/modules/blockchain/ — BLOCKCHAIN_ENABLED=false, no web3 lib",
    status:"Code complete, no real chain, no web3/ethers in requirements",
    prompt:`You are in the VIT Sports Intelligence Network repo.

TASK: Connect VIT to Base L2 (Coinbase's L2) using $2 budget. Base has near-zero gas fees (~$0.001/tx).

STEP 1 — Add to requirements.txt:
web3==7.6.0

STEP 2 — Create app/services/base_chain.py:
\`\`\`python
"""Base L2 (chain_id=8453) connection for VITCoin on-chain operations."""
import os
from web3 import Web3
from web3.middleware import geth_poa_middleware

BASE_RPC = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")  # free public RPC
BASE_CHAIN_ID = 8453

_w3 = None

def get_w3() -> Web3:
    global _w3
    if _w3 is None:
        _w3 = Web3(Web3.HTTPProvider(BASE_RPC))
        _w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return _w3

def is_connected() -> bool:
    try:
        return get_w3().is_connected()
    except Exception:
        return False

def get_block_number() -> int:
    return get_w3().eth.block_number

def get_eth_balance(address: str) -> float:
    """Returns ETH balance in ether (not wei)."""
    w3 = get_w3()
    bal = w3.eth.get_balance(Web3.to_checksum_address(address))
    return float(w3.from_wei(bal, 'ether'))

VITCOIN_CONTRACT_ADDRESS = os.getenv("VITCOIN_CONTRACT_ADDRESS", "")

VITCOIN_ABI = [
    {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
]

def get_vitcoin_contract():
    if not VITCOIN_CONTRACT_ADDRESS:
        return None
    w3 = get_w3()
    return w3.eth.contract(
        address=Web3.to_checksum_address(VITCOIN_CONTRACT_ADDRESS),
        abi=VITCOIN_ABI
    )

def get_vitcoin_balance(wallet_address: str) -> float:
    contract = get_vitcoin_contract()
    if not contract:
        return 0.0
    try:
        raw = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        decimals = contract.functions.decimals().call()
        return raw / (10 ** decimals)
    except Exception:
        return 0.0
\`\`\`

STEP 3 — Add GET /api/blockchain/chain-status endpoint:
\`\`\`python
@router.get("/chain-status")
async def chain_status():
    from app.services.base_chain import is_connected, get_block_number
    connected = is_connected()
    return {
        "network": "Base L2",
        "chain_id": 8453,
        "connected": connected,
        "block": get_block_number() if connected else None,
        "rpc": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
    }
\`\`\`

STEP 4 — Replit Secrets:
BASE_RPC_URL = https://mainnet.base.org   (free, no key needed)
BLOCKCHAIN_ENABLED = true

STEP 5 — Deploy VITCoin ERC-20 (budget: $2 on Base = ~2000 transactions):
Use Remix IDE (remix.ethereum.org) → Deploy this contract on Base Mainnet:
\`\`\`solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract VITCoin is ERC20, Ownable {
    constructor(address initialOwner) ERC20("VITCoin", "VIT") Ownable(initialOwner) {
        _mint(initialOwner, 100_000_000 * 10**18); // 100M VIT
    }
    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
\`\`\`
After deploy: VITCOIN_CONTRACT_ADDRESS = 0x... (copy from Remix)

STEP 6 — Update feature_flags: BLOCKCHAIN_ENABLED must now be read from env:
In app/core/feature_flags.py ensure: FeatureFlags.is_enabled("BLOCKCHAIN_ENABLED")
Set BLOCKCHAIN_ENABLED=true in Replit Secrets after contract is deployed.

VERIFY: GET /api/blockchain/chain-status → {"connected": true, "block": 28000000+}`
  },
  {
    id:"G07", sev:"HIGH", cat:"AI",
    title:"Multi-AI dispatcher: Claude/Grok keys missing — Gemini-only fallback",
    location:"app/services/multi_ai_dispatcher.py + claude_insights.py + grok_insights.py",
    status:"Code complete, keys not set in .env.example or Replit Secrets",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: multi_ai_dispatcher.py tries Claude (ANTHROPIC_API_KEY), Grok (XAI_API_KEY), and Gemini in parallel. If the first two keys are missing, all insight requests silently return Gemini-only. The AI comparison panel shows 1 provider instead of 3.

FIX 1 — app/services/claude_insights.py — verify it uses correct env var:
\`\`\`python
import os
import anthropic

async def generate_match_insights(home_team, away_team, league, home_prob, draw_prob, away_prob, **kwargs):
    api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"available": False, "provider": "claude", "error": "CLAUDE_API_KEY not set"}
    
    client = anthropic.AsyncAnthropic(api_key=api_key)
    prompt = f"""Football match analysis for {home_team} vs {away_team} ({league}).
Probabilities: Home {home_prob:.1%} | Draw {draw_prob:.1%} | Away {away_prob:.1%}
Provide: 3 key factors, main risk, confidence rating (1-5), one verdict sentence. Max 120 words."""
    
    try:
        msg = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=250,
            messages=[{"role":"user","content":prompt}]
        )
        return {"available": True, "provider": "claude", "insight": msg.content[0].text}
    except Exception as e:
        return {"available": False, "provider": "claude", "error": str(e)}
\`\`\`

FIX 2 — Add to requirements.txt: anthropic==0.40.0

REQUIRED Replit Secrets:
- CLAUDE_API_KEY = sk-ant-api03-...  (console.anthropic.com)
- XAI_API_KEY = xai-...              (x.ai/api)
- GEMINI_API_KEY = AIza...           (aistudio.google.com)

FIX 3 — multi_ai_dispatcher.py — add 10s timeout per provider:
\`\`\`python
results = await asyncio.gather(
    *[asyncio.wait_for(_call_provider(p, kwargs), timeout=10.0) for p in providers],
    return_exceptions=True
)
\`\`\`

VERIFY: POST /api/ai/insights {"match_id": 1}
Response should show providers: ["claude", "gemini", "grok"] all with available: true`
  },
  {
    id:"G08", sev:"HIGH", cat:"Frontend",
    title:"Offerwall page empty — 5 providers integrated in backend, no frontend",
    location:"frontend/src/pages/offerwall.tsx — page exists but has no provider content",
    status:"Backend postbacks complete, frontend page shows nothing",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: frontend/src/pages/offerwall.tsx exists but renders no content. The backend has 5 offerwall providers (Ayet, Tapjoy, RevU, BitLabs, CPX) with full postback handling. Users cannot see or access any offers.

REPLACE frontend/src/pages/offerwall.tsx with full implementation:
\`\`\`tsx
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";

const PROVIDERS = [
  { id:"ayet",    name:"Ayet Studios",  icon:"🎮", color:"#f59e0b", desc:"Complete offers & surveys for VITCoin",  rate:"Up to 50 VIT/offer" },
  { id:"tapjoy",  name:"Tapjoy",        icon:"📱", color:"#10b981", desc:"Install apps and complete challenges",   rate:"Up to 30 VIT/install" },
  { id:"revu",    name:"RevU",          icon:"📊", color:"#6366f1", desc:"Market research & consumer surveys",    rate:"5–20 VIT/survey" },
  { id:"bitlabs", name:"BitLabs",       icon:"💡", color:"#ec4899", desc:"Premium targeted surveys",              rate:"10–40 VIT/survey" },
  { id:"cpx",     name:"CPX Research",  icon:"🔬", color:"#06b6d4", desc:"Academic & consumer research panels",  rate:"5–25 VIT/survey" },
];

export default function OfferwallPage() {
  const { user } = useAuth();
  const { data: completions = [] } = useQuery({
    queryKey: ["my-offer-completions"],
    queryFn: () => apiGet<any[]>("/api/rewards/my-completions"),
    staleTime: 30_000,
  });
  
  const earned = completions.filter(c => c.status === "credited").reduce((s,c) => s + (c.vitcoin_amount || 0), 0);
  const pending = completions.filter(c => c.status === "pending").length;

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <div>
        <h1 className="text-2xl font-black text-white">Earn VITCoin</h1>
        <p className="text-sm text-muted-foreground mt-1">Complete offers and surveys to earn VITCoin rewards</p>
      </div>
      
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Earned", value: earned.toFixed(1) + " VIT", color: "text-yellow-400" },
          { label: "Completed", value: completions.filter(c=>c.status==="credited").length, color: "text-green-400" },
          { label: "Pending", value: pending, color: "text-orange-400" },
        ].map(s => (
          <div key={s.label} className="bg-card border rounded-xl p-4 text-center">
            <div className={"text-2xl font-black " + s.color}>{s.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
          </div>
        ))}
      </div>
      
      <div className="grid gap-3">
        {PROVIDERS.map(p => (
          <div key={p.id} className="bg-card border rounded-xl p-4 flex items-center gap-4 hover:border-primary/50 transition-colors">
            <div className="text-4xl">{p.icon}</div>
            <div className="flex-1">
              <div className="font-bold text-white">{p.name}</div>
              <div className="text-sm text-muted-foreground">{p.desc}</div>
              <div className="text-xs font-mono mt-1" style={{color: p.color}}>{p.rate}</div>
            </div>
            <button
              className="px-4 py-2 rounded-lg font-bold text-sm text-black"
              style={{background: p.color}}
              onClick={() => window.open(\`/api/rewards/offerwall/\${p.id}?user_id=\${user?.id}\`, '_blank')}
            >
              Start Earning →
            </button>
          </div>
        ))}
      </div>
      
      {completions.length > 0 && (
        <div>
          <h2 className="font-bold text-white mb-3">Recent Completions</h2>
          <div className="space-y-2">
            {completions.slice(0,10).map((c,i) => (
              <div key={i} className="flex items-center gap-3 bg-card border rounded-lg px-4 py-2 text-sm">
                <span className="font-bold text-yellow-400">+{c.vitcoin_amount?.toFixed(1)} VIT</span>
                <span className="text-muted-foreground flex-1 capitalize">{c.provider_name}</span>
                <span className={\`text-xs px-2 py-0.5 rounded font-bold \${c.status==="credited"?"bg-green-900/50 text-green-400":"bg-yellow-900/50 text-yellow-400"}\`}>{c.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
\`\`\`

Also ADD GET /api/rewards/my-completions endpoint in app/modules/rewards/routes.py:
\`\`\`python
@router.get("/my-completions")
async def my_completions(current_user=Depends(get_current_user), db=Depends(get_db)):
    rows = (await db.execute(
        select(OfferCompletion).where(OfferCompletion.user_id==current_user.id).order_by(OfferCompletion.created_at.desc()).limit(50)
    )).scalars().all()
    return [{"provider_name": r.provider_name, "vitcoin_amount": float(r.vitcoin_amount or 0), "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]
\`\`\``
  },
  {
    id:"G09", sev:"HIGH", cat:"Developer",
    title:"Developer API billing never deducts VITCoin per API call",
    location:"app/modules/developer/service.py — price_vitcoin_per_1k defined, never called",
    status:"Schema complete, billing middleware not wired to request path",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: Developer API keys have price_vitcoin_per_1k set but the middleware never deducts VITCoin. vitcoin_billed stays 0 forever. The billing model exists but the deduction call is missing.

FIX app/api/middleware/auth.py — after validating a developer API key:
\`\`\`python
# After successful key lookup, add billing deduction:
if dev_key:
    svc = DeveloperService(db)
    try:
        await svc.bill_api_call(dev_key.id, dev_key.user_id, 1)
    except InsufficientVITCoinError:
        return JSONResponse({"detail": "Insufficient VITCoin balance. Top up to continue using the API."}, status_code=402)
\`\`\`

ADD to app/modules/developer/service.py:
\`\`\`python
async def bill_api_call(self, key_id: int, user_id: int, calls: int = 1) -> None:
    key = await self._get_key(key_id)
    cost = Decimal(str(key.price_vitcoin_per_1k)) * calls / 1000
    if cost == 0:
        return  # free tier
    # Update usage counter
    key.total_calls += calls
    key.vitcoin_billed = (key.vitcoin_billed or Decimal("0")) + cost
    # Deduct from wallet
    wallet_svc = WalletService(self.db)
    await wallet_svc.deduct(user_id, "VIT", cost, "api_billing", f"API call {key.key_prefix}")
    await self.db.commit()
\`\`\`

VERIFY: Make an API call with a developer key → GET /api/developer/usage/stats → vitcoin_billed increases`
  },
  {
    id:"G10", sev:"HIGH", cat:"Governance",
    title:"Governance proposals have no quorum check and no execution engine",
    location:"app/modules/governance/service.py + routes.py",
    status:"Voting works, quorum=0, no executor, proposals are cosmetic",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: Governance proposals pass with 0 quorum. Approved proposals never execute — change_payload is stored but never read. The governance DAO is purely cosmetic.

FIX 1 — app/modules/governance/service.py — add quorum enforcement:
\`\`\`python
QUORUM_PCT = Decimal("0.10")  # 10% of total VITCoin supply must vote

async def close_voting(self, proposal_id: int) -> dict:
    proposal = await self._get(proposal_id)
    total_supply = await WalletService(self.db).get_total_vitcoin_supply()
    quorum_required = total_supply * QUORUM_PCT
    
    if proposal.total_votes_vitcoin < quorum_required:
        proposal.status = "failed_quorum"
        await self.db.commit()
        return {"status": "failed_quorum", "votes": float(proposal.total_votes_vitcoin), "required": float(quorum_required)}
    
    if proposal.votes_for > proposal.votes_against:
        proposal.status = "approved"
        proposal.execution_after = datetime.now(timezone.utc) + timedelta(hours=48)  # 48h timelock
    else:
        proposal.status = "rejected"
    await self.db.commit()
    return {"status": proposal.status}
\`\`\`

FIX 2 — Add proposal executor (runs after timelock):
\`\`\`python
async def execute_proposal(self, proposal_id: int) -> dict:
    proposal = await self._get(proposal_id)
    if proposal.status != "approved":
        raise HTTPException(400, "Proposal not approved")
    if proposal.execution_after > datetime.now(timezone.utc):
        raise HTTPException(425, f"Timelock active until {proposal.execution_after.isoformat()}")
    
    payload = proposal.change_payload or {}
    action = payload.get("action")
    
    if action == "update_subscription_price":
        plan = payload["plan"]; new_price = payload["price_monthly"]
        await db.execute(update(SubscriptionPlan).where(SubscriptionPlan.name==plan).values(price_monthly=new_price))
    elif action == "update_feature_flag":
        flag = payload["flag"]; value = payload["value"]
        os.environ[flag] = str(value)
        FeatureFlags._flags[flag] = value == "true"
    # Add more action types as needed
    
    proposal.status = "executed"
    proposal.executed_at = datetime.now(timezone.utc)
    await self.db.commit()
    return {"status": "executed", "action": action}
\`\`\`

ADD endpoint: POST /api/governance/proposals/{id}/execute (admin-only)`
  },
  {
    id:"G11", sev:"MEDIUM", cat:"Trust",
    title:"Trust engine scores users but never takes automated actions",
    location:"app/modules/trust/engine.py — score calculated, no suspend/flag logic",
    status:"Score calculation works, action thresholds unused",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: TrustEngine calculates a 0-100 score per user. But no automated actions fire based on score. A user with trust_score=5 (known fraudster) still has full platform access.

ADD to app/modules/trust/engine.py after score update:
\`\`\`python
THRESHOLDS = {
    "auto_flag":    30,  # flag for manual review
    "auto_freeze":  15,  # freeze withdrawals
    "auto_suspend": 5,   # suspend account
}

async def apply_trust_actions(self, db: AsyncSession, user_id: int, score: float) -> list[str]:
    actions_taken = []
    user = await db.get(User, user_id)
    if not user:
        return actions_taken
    
    if score <= THRESHOLDS["auto_suspend"] and not user.is_suspended:
        user.is_suspended = True
        user.suspension_reason = f"Auto-suspended: trust score {score:.1f}"
        actions_taken.append("auto_suspended")
        await notify_admin(f"User {user_id} auto-suspended, trust score={score:.1f}")
    
    elif score <= THRESHOLDS["auto_freeze"] and not user.withdrawals_frozen:
        user.withdrawals_frozen = True
        actions_taken.append("withdrawals_frozen")
    
    elif score <= THRESHOLDS["auto_flag"] and not user.is_flagged:
        user.is_flagged = True
        actions_taken.append("flagged_for_review")
    
    await db.commit()
    return actions_taken
\`\`\`

Call apply_trust_actions() at end of recalculate_score().
Add is_flagged, withdrawals_frozen columns to users table via Alembic migration.`
  },
  {
    id:"G12", sev:"MEDIUM", cat:"KYC",
    title:"KYC sets status=pending but no real identity verification provider",
    location:"app/modules/wallet/routes.py L404 — stores document_type only",
    status:"Data stored, no Smile Identity / Onfido SDK, admin UI missing",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: POST /api/wallet/kyc/submit stores document_type and raw data, sets kyc_status='pending', but there is no identity verification provider call. Withdrawal limits can never be lifted. There is no admin UI to approve/reject.

FIX 1 — app/modules/wallet/routes.py — KYC submit (Smile Identity free sandbox):
\`\`\`python
import httpx, os

SMILE_PARTNER_ID = os.getenv("SMILE_PARTNER_ID", "")
SMILE_API_KEY = os.getenv("SMILE_API_KEY", "")

async def _submit_to_smile_identity(user, kyc_data: dict) -> dict:
    if not SMILE_PARTNER_ID:
        return {"status": "pending_manual", "provider": "none"}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://testapi.smileidentity.com/v1/id_verification",
            json={
                "partner_id": SMILE_PARTNER_ID,
                "partner_params": {"user_id": str(user.id), "job_id": f"vit-kyc-{user.id}", "job_type": 5},
                "id_info": {
                    "first_name": kyc_data.get("first_name"),
                    "last_name": kyc_data.get("last_name"),
                    "country": kyc_data.get("country", "NG"),
                    "id_type": kyc_data.get("document_type", "PASSPORT").upper(),
                    "id_number": kyc_data.get("id_number"),
                },
                "options": {"return_job_status": True}
            },
            headers={"Authorization": f"Bearer {SMILE_API_KEY}"},
            timeout=30,
        )
    result = r.json()
    if result.get("result", {}).get("ResultCode") == "1012":
        return {"status": "approved", "provider": "smile_identity"}
    return {"status": "pending", "provider": "smile_identity", "raw": result}
\`\`\`

FIX 2 — Admin KYC review endpoint:
\`\`\`python
@admin_router.patch("/kyc/{user_id}/decision")
async def kyc_decision(user_id: int, approved: bool, note: str = "", admin=Depends(require_admin), db=Depends(get_db)):
    user = await db.get(User, user_id)
    user.kyc_status = "approved" if approved else "rejected"
    user.kyc_note = note
    if approved:
        user.withdrawal_limit_daily = Decimal("50000")  # lift limit
    await db.commit()
    return {"status": user.kyc_status}
\`\`\`

Replit Secrets: SMILE_PARTNER_ID, SMILE_API_KEY (smileidentity.com free sandbox)`
  },
  {
    id:"G13", sev:"MEDIUM", cat:"Frontend",
    title:"2FA setup has no frontend flow — backend TOTP complete",
    location:"frontend/src/pages/settings.tsx — no 2FA component wired",
    status:"Backend /auth/2fa/setup + /enable complete, no UI",
    prompt:`You are in the VIT Sports Intelligence Network repo.

PROBLEM: The backend TOTP endpoints (/auth/2fa/setup, /auth/2fa/enable, /auth/2fa/disable) are complete with QR code generation. But frontend/src/pages/settings.tsx has no 2FA section.

ADD to frontend/src/pages/settings.tsx:
\`\`\`tsx
import { useState } from "react";
import { apiPost } from "@/lib/apiClient";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

function TwoFactorSection({ totp_enabled }: { totp_enabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"qr"|"verify"|"done">("qr");
  const [qrUrl, setQrUrl] = useState("");
  const [code, setCode] = useState("");
  const { toast } = useToast();

  async function startSetup() {
    const res = await apiPost<{qr_data_url: string}>("/auth/2fa/setup", {});
    setQrUrl(res.qr_data_url);
    setStep("qr");
    setOpen(true);
  }

  async function verifyCode() {
    try {
      await apiPost("/auth/2fa/enable", { totp_code: code });
      setStep("done");
      toast({ title: "2FA enabled!", description: "Your account is now protected." });
    } catch {
      toast({ title: "Invalid code", description: "Try again.", variant: "destructive" });
    }
  }

  if (totp_enabled) return (
    <div className="flex items-center gap-3 p-4 rounded-xl border border-green-800 bg-green-950/30">
      <span className="text-green-400 text-xl">🔐</span>
      <div className="flex-1">
        <div className="font-semibold text-green-300">2FA Active</div>
        <div className="text-xs text-green-700">Authenticator app is protecting your account</div>
      </div>
      <Button size="sm" variant="outline" className="text-red-400 border-red-800"
        onClick={async () => { await apiPost("/auth/2fa/disable", {}); window.location.reload(); }}>
        Disable
      </Button>
    </div>
  );

  return (
    <>
      <div className="flex items-center gap-3 p-4 rounded-xl border border-border bg-card">
        <span className="text-2xl">🔓</span>
        <div className="flex-1">
          <div className="font-semibold">Two-Factor Authentication</div>
          <div className="text-xs text-muted-foreground">Add an extra layer of security</div>
        </div>
        <Button size="sm" onClick={startSetup}>Enable 2FA</Button>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Set Up 2FA</DialogTitle></DialogHeader>
          {step === "qr" && <>
            <p className="text-sm text-muted-foreground">Scan with Google Authenticator or Authy:</p>
            {qrUrl && <img src={qrUrl} className="mx-auto w-48 h-48 rounded-xl" />}
            <Button onClick={() => setStep("verify")}>I've scanned it →</Button>
          </>}
          {step === "verify" && <>
            <p className="text-sm text-muted-foreground">Enter the 6-digit code:</p>
            <Input value={code} onChange={e=>setCode(e.target.value)} placeholder="000000"
              maxLength={6} className="text-center text-3xl tracking-[0.5em] font-mono" />
            <Button onClick={verifyCode}>Verify & Enable</Button>
          </>}
          {step === "done" && <p className="text-center text-green-400 font-bold text-lg">✅ 2FA Enabled!</p>}
        </DialogContent>
      </Dialog>
    </>
  );
}
\`\`\`
Add <TwoFactorSection totp_enabled={user?.totp_enabled ?? false} /> in the Security section of settings.tsx`
  },
  {
    id:"G14", sev:"MEDIUM", cat:"ML",
    title:"USE_REAL_ML_MODELS=false — all predictions use statistical priors",
    location:".replit + services/ml_service/models/model_orchestrator.py",
    status:"Train scripts exist, no .pkl weights uploaded, flag off",
    prompt:`You are in the VIT Sports Intelligence Network repo.

TASK: Train real model weights and activate them. You have 9,000+ training rows in data/raw/*.csv.

STEP 1 — Run the training pipeline:
\`\`\`bash
python scripts/generate_training_data.py --source data/raw --output data/historical_matches_training.csv
python scripts/train_models.py --data data/historical_matches_training.csv --output models/ --models logistic_v1,rf_v1,xgb_v1,gbm_v1,lgbm_v1
python scripts/fit_calibrators_from_csv.py --data data/historical_matches_training.csv
\`\`\`

STEP 2 — Upload each .pkl via Admin API:
\`\`\`bash
for key in logistic_v1 rf_v1 xgb_v1 gbm_v1 lgbm_v1; do
  curl -X POST "http://localhost:5000/api/ai-engine/upload/$key" \\
    -H "Authorization: Bearer \$ADMIN_TOKEN" \\
    -F "file=@models/\${key}.pkl" \\
    -F "auto_promote=true"
done
\`\`\`

STEP 3 — Set in Replit Secrets: USE_REAL_ML_MODELS = true

STEP 4 — Trigger daily weight adjustment:
POST /api/ai-engine/weights/adjust {"days_back": 30}

VERIFY: GET /api/ai-engine/status → all 5+ models show pkl_loaded=true, accuracy > 0.54
VERIFY: POST /api/predict → predictions now show distinct per-model probabilities`
  },
  {
    id:"G15", sev:"MEDIUM", cat:"Data",
    title:"FOOTBALL_DATA_API_KEY missing — fixture sync fails silently",
    location:"app/services/football_api.py — key not set in most deployments",
    status:"Free API tier available, key just not configured",
    prompt:`You are in the VIT Sports Intelligence Network repo.

TASK: Set up Football-Data.org API (free: 10 req/min, 12 competitions).

STEP 1 — Sign up at football-data.org → get free API key (instant, no credit card)

STEP 2 — Replit Secrets: FOOTBALL_DATA_API_KEY = your_key_here

STEP 3 — Test the connection:
POST /admin/data-sources/test/football_data → should return {"status": "ok", "plan": "free"}

STEP 4 — Import fixtures for upcoming week:
POST /admin/matches/sync-fixtures?days_ahead=7

STEP 5 — Also set up The Odds API (free: 500 req/month):
Sign up at the-odds-api.com → REPLIT SECRET: THE_ODDS_API_KEY = your_key

STEP 6 — Import odds for upcoming matches:
POST /admin/odds/refresh-all

VERIFY: GET /api/matches?status=upcoming → should show 20+ real upcoming matches with odds`
  },
];

// ─── BASE BLOCKCHAIN GUIDE ─────────────────────────────────────────
const BASE_GUIDE = {
  title: "Going Live on Base L2 — $2 Budget Plan",
  budget: "$2.00 ETH on Base",
  network: "Base Mainnet (Chain ID: 8453)",
  costs: [
    { item: "Deploy VITCoin ERC-20 contract", cost: "~$0.30", note: "One-time deployment" },
    { item: "Mint 100M VIT to treasury address", cost: "~$0.10", note: "Initial supply" },
    { item: "Set contract owner to multisig", cost: "~$0.05", note: "Security step" },
    { item: "Reserve for 200 on-chain transactions", cost: "~$0.20 each × 5", note: "Bridge operations" },
    { item: "Buffer remaining", cost: "~$1.25", note: "Gas price spikes, future ops" },
  ],
  steps: [
    { n:1, title:"Bridge ETH to Base", detail:"Use bridge.base.org to move $2 ETH from Ethereum mainnet to Base. Takes ~3 min. Zero bridge fee for small amounts." },
    { n:2, title:"Open Remix IDE", detail:"Go to remix.ethereum.org in browser. Create VITCoin.sol using the ERC-20 contract from G06 prompt. Import OpenZeppelin via npm in Remix." },
    { n:3, title:"Connect MetaMask to Base Mainnet", detail:"Add Base Mainnet to MetaMask: RPC https://mainnet.base.org, Chain ID 8453, Symbol ETH, Explorer https://basescan.org" },
    { n:4, title:"Deploy Contract", detail:'In Remix → Deploy & Run → Environment: "Injected Provider (MetaMask)" → Select Base network → Deploy VITCoin(your_address) → Confirm transaction in MetaMask (~$0.30)' },
    { n:5, title:"Verify on BaseScan", detail:"After deploy, copy contract address. Go to basescan.org/address/0x... → Verify & Publish → Paste source code. Verified contracts show green checkmark and are publicly readable." },
    { n:6, title:"Add to Replit Secrets", detail:"VITCOIN_CONTRACT_ADDRESS = 0x... (from Remix)\nBLOCKCHAIN_ENABLED = true\nBASE_RPC_URL = https://mainnet.base.org" },
    { n:7, title:"Test bridge (internal → on-chain)", detail:"POST /api/wallet/bridge/to-chain {amount: 10, wallet_address: '0x...'} → Should call VITCoin.transfer() on Base. Verify on BaseScan." },
  ],
  freeTools: [
    { name:"Base Public RPC", url:"https://mainnet.base.org", desc:"Free, no API key needed" },
    { name:"BaseScan Explorer", url:"https://basescan.org", desc:"Free contract verification" },
    { name:"Remix IDE", url:"https://remix.ethereum.org", desc:"Free browser-based Solidity IDE" },
    { name:"Base Bridge", url:"https://bridge.base.org", desc:"Official ETH → Base bridge" },
    { name:"OpenZeppelin Contracts", url:"https://openzeppelin.com/contracts", desc:"Free audited ERC-20 base" },
  ],
};

// ─── COMPONENT ─────────────────────────────────────────────────────
const sevColor = { CRITICAL:"#ef4444", HIGH:"#f97316", MEDIUM:"#eab308" };
const sevBg = { CRITICAL:"bg-red-950/60 border-red-800", HIGH:"bg-orange-950/60 border-orange-800", MEDIUM:"bg-yellow-950/60 border-yellow-800" };
const catColors = {
  Security:"#ef4444", Infrastructure:"#6366f1", Payments:"#10b981",
  Auth:"#8b5cf6", Blockchain:"#f59e0b", AI:"#06b6d4",
  Frontend:"#ec4899", Developer:"#14b8a6", Governance:"#a78bfa",
  Trust:"#fb923c", KYC:"#34d399", ML:"#818cf8", Data:"#67e8f9",
};

function GapCard({ gap }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const cc = catColors[gap.cat] || "#888";

  const copy = () => {
    navigator.clipboard.writeText(gap.prompt);
    setCopied(true); setTimeout(()=>setCopied(false),2000);
  };

  return (
    <div className={`rounded-xl border overflow-hidden transition-all ${sevBg[gap.sev]}`} style={{borderColor:sevColor[gap.sev]+"44"}}>
      <button className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-white/5 transition" onClick={()=>setOpen(!open)}>
        <span className="text-xs font-black px-2 py-0.5 rounded-full" style={{background:sevColor[gap.sev]+"33",color:sevColor[gap.sev]}}>{gap.sev}</span>
        <span className="text-xs font-mono text-gray-500">{gap.id}</span>
        <span className="text-xs px-2 py-0.5 rounded font-bold" style={{background:cc+"22",color:cc}}>{gap.cat}</span>
        <span className="flex-1 text-sm font-semibold text-white truncate">{gap.title}</span>
        <span className="text-gray-600 text-xs italic hidden sm:block shrink-0">{gap.status}</span>
        <span className="text-gray-500 ml-1">{open?"▲":"▼"}</span>
      </button>
      {open && (
        <div className="border-t border-white/10">
          <div className="px-4 py-2 bg-white/5 text-xs text-gray-400 font-mono">{gap.location}</div>
          <div className="relative">
            <pre className="px-4 py-4 text-xs text-gray-300 overflow-auto whitespace-pre-wrap leading-relaxed" style={{maxHeight:"420px",fontFamily:"'JetBrains Mono',monospace"}}>
              {gap.prompt}
            </pre>
            <button onClick={copy}
              className="absolute top-3 right-3 px-3 py-1.5 text-xs font-black rounded-lg transition text-black"
              style={{background:copied?"#10b981":sevColor[gap.sev]}}>
              {copied?"✓ COPIED":"📋 COPY"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VITMasterPrompt() {
  const [tab, setTab] = useState("gaps");
  const [filter, setFilter] = useState("ALL");
  const cats = ["ALL","CRITICAL","HIGH","MEDIUM"];

  const counts = {CRITICAL:GAPS.filter(g=>g.sev==="CRITICAL").length, HIGH:GAPS.filter(g=>g.sev==="HIGH").length, MEDIUM:GAPS.filter(g=>g.sev==="MEDIUM").length};
  const filtered = filter==="ALL" ? GAPS : GAPS.filter(g=>g.sev===filter);

  return (
    <div className="min-h-screen bg-[#080b10] text-gray-100" style={{fontFamily:"'JetBrains Mono',monospace"}}>
      {/* HEADER */}
      <div className="sticky top-0 z-20 bg-[#080b10]/95 backdrop-blur border-b border-white/8">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 mr-2">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"/>
            <span className="text-xs font-black tracking-widest text-white">VIT OS MASTER FIX</span>
          </div>
          <div className="flex gap-1.5">
            <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-950 text-red-400 border border-red-800">{counts.CRITICAL} CRITICAL</span>
            <span className="px-2 py-0.5 rounded text-xs font-bold bg-orange-950 text-orange-400 border border-orange-800">{counts.HIGH} HIGH</span>
            <span className="px-2 py-0.5 rounded text-xs font-bold bg-yellow-950 text-yellow-400 border border-yellow-800">{counts.MEDIUM} MEDIUM</span>
          </div>
          <div className="ml-auto flex gap-1">
            {["gaps","blockchain"].map(t=>(
              <button key={t} onClick={()=>setTab(t)}
                className={`px-3 py-1 text-xs font-bold rounded-lg transition ${tab===t?"bg-white text-black":"text-gray-400 hover:text-white"}`}>
                {t==="gaps"?"🔧 Fix Gaps":"⛓️ Base Blockchain"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6">

        {/* GAPS TAB */}
        {tab==="gaps" && (
          <>
            <div className="mb-5">
              <div className="text-xs text-gray-500 mb-3 uppercase tracking-wider">Filter by severity — click any card to expand the Replit Agent prompt</div>
              <div className="flex gap-2 flex-wrap">
                {cats.map(c=>(
                  <button key={c} onClick={()=>setFilter(c)}
                    className={`px-3 py-1 text-xs font-bold rounded-lg border transition ${filter===c?"text-black border-transparent":"border-white/15 text-gray-400 hover:text-white"}`}
                    style={filter===c?{background:c==="ALL"?"#fff":sevColor[c],borderColor:c==="ALL"?"#fff":sevColor[c]}:{}}>
                    {c} {c!=="ALL"?`(${counts[c]})`:`(${GAPS.length})`}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              {filtered.map(g=><GapCard key={g.id} gap={g}/>)}
            </div>
          </>
        )}

        {/* BLOCKCHAIN TAB */}
        {tab==="blockchain" && (
          <div className="space-y-6">
            {/* Hero */}
            <div className="rounded-2xl border border-yellow-700/50 bg-yellow-950/20 p-5"
              style={{background:"linear-gradient(135deg,rgba(245,158,11,0.1) 0%,rgba(0,0,0,0) 60%)"}}>
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="text-xs text-yellow-500 font-bold uppercase tracking-widest mb-1">Base Network Go-Live</div>
                  <div className="text-2xl font-black text-white">{BASE_GUIDE.title}</div>
                  <div className="text-sm text-yellow-400 mt-1">{BASE_GUIDE.network}</div>
                </div>
                <div className="text-center bg-black/40 rounded-xl px-5 py-3 border border-yellow-800">
                  <div className="text-3xl font-black text-yellow-400">{BASE_GUIDE.budget}</div>
                  <div className="text-xs text-yellow-700 mt-1">Total Budget</div>
                </div>
              </div>
            </div>

            {/* Cost breakdown */}
            <div className="rounded-xl border border-white/10 bg-black/30 overflow-hidden">
              <div className="px-4 py-3 border-b border-white/10 text-xs font-bold uppercase tracking-wider text-gray-400">Cost Breakdown</div>
              <div className="divide-y divide-white/5">
                {BASE_GUIDE.costs.map((c,i)=>(
                  <div key={i} className="px-4 py-3 flex items-center gap-3">
                    <div className="flex-1 text-sm text-gray-300">{c.item}</div>
                    <div className="text-xs text-gray-500 hidden sm:block">{c.note}</div>
                    <div className="font-bold text-yellow-400 font-mono text-sm w-16 text-right">{c.cost}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Steps */}
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Step-by-Step Launch</div>
              <div className="space-y-3">
                {BASE_GUIDE.steps.map(s=>(
                  <div key={s.n} className="flex gap-3 rounded-xl border border-white/10 bg-black/30 p-4">
                    <div className="w-7 h-7 rounded-full bg-yellow-500 text-black font-black text-xs flex items-center justify-center shrink-0 mt-0.5">{s.n}</div>
                    <div>
                      <div className="font-bold text-white text-sm">{s.title}</div>
                      <div className="text-xs text-gray-400 mt-1 leading-relaxed whitespace-pre-line">{s.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Free tools */}
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Free Tools (no cost)</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {BASE_GUIDE.freeTools.map(t=>(
                  <div key={t.name} className="flex items-center gap-3 rounded-lg border border-white/10 bg-black/30 px-3 py-2">
                    <div className="w-2 h-2 rounded-full bg-green-400"/>
                    <div>
                      <div className="text-sm font-bold text-white">{t.name}</div>
                      <div className="text-xs text-gray-500">{t.desc}</div>
                    </div>
                    <code className="ml-auto text-xs text-cyan-400 hidden sm:block">{t.url.replace("https://","")}</code>
                  </div>
                ))}
              </div>
            </div>

            {/* Copy G06 prompt */}
            <div className="rounded-xl border border-yellow-700/50 bg-black/40 p-4">
              <div className="text-sm font-bold text-yellow-300 mb-2">Full Replit Agent Prompt for Base Integration</div>
              <div className="text-xs text-gray-400 mb-3">Copy gap G06 above — it contains the complete web3.py code, ERC-20 Solidity contract, and all Replit Secrets needed.</div>
              <button onClick={()=>setTab("gaps")} className="px-4 py-2 bg-yellow-500 text-black font-bold text-xs rounded-lg">
                ← Go to G06 Blockchain Prompt
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
