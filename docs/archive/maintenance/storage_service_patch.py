import sys
import os

path = 'app/modules/storage_verification/service.py'
with open(path, 'r') as f:
    content = f.read()

# Add imports
imports = """from app.modules.storage_verification.models import (
    ChallengeStatus,
    ContentHashRegistry,
    DataAvailabilityAttestation,
    StorageChallenge,
    StorageProof,
    StorageProofStatus,
    UserStorageNode,
)
from app.modules.wallet.services import WalletService"""

if 'from app.modules.wallet.services import WalletService' not in content:
    content = content.replace(
        'from app.modules.storage_verification.models import (',
        imports
    ).replace(
        '    StorageProofStatus,\n)',
        '    StorageProofStatus,'
    )

# Patch respond_to_challenge
search_text = """    proof = await db.get(StorageProof, challenge.proof_id)
    if proof:
        if valid:
            proof.status = StorageProofStatus.VERIFIED
            proof.verified_at = datetime.now(timezone.utc)
            reward = proof.stake_locked * Decimal("0.1")
            proof.reward_earned = reward
        else:
            proof.status = StorageProofStatus.FAILED
            challenge.slash_amount = proof.stake_locked

    await db.commit()"""

replace_text = """    proof = await db.get(StorageProof, challenge.proof_id)
    if proof:
        if valid:
            proof.status = StorageProofStatus.VERIFIED
            proof.verified_at = datetime.now(timezone.utc)
            reward = proof.stake_locked * Decimal("0.1")
            proof.reward_earned = reward

            # VESS Core: Automate VITCoin (TSC) incentive distribution
            if proof.prover_user_id:
                try:
                    ws = WalletService(db)
                    await ws.deposit_vitcoin(
                        user_id=proof.prover_user_id,
                        amount=float(reward),
                        description=f"Storage Proof Reward: {proof.proof_hash[:8]}",
                        tx_type="reward",
                        metadata={"proof_id": proof.id, "challenge_id": challenge_id}
                    )

                    # Update UserStorageNode stats if applicable
                    node_q = select(UserStorageNode).where(
                        UserStorageNode.user_id == proof.prover_user_id,
                        UserStorageNode.status == "active"
                    ).limit(1)
                    node = (await db.execute(node_q)).scalar_one_or_none()
                    if node:
                        node.tsc_earned += reward
                        node.verification_count += 1
                        node.verification_pass += 1
                        node.last_verified_at = datetime.now(timezone.utc)
                        # Calculate reliability score (EWMA style)
                        node.reliability_score = Decimal(str(min(1.0, float(node.reliability_score) * 0.95 + 0.05)))
                except Exception as e:
                    logger.error("[vess] incentive distribution failed: %s", e)
        else:
            proof.status = StorageProofStatus.FAILED
            challenge.slash_amount = proof.stake_locked

            if proof.prover_user_id:
                node_q = select(UserStorageNode).where(
                    UserStorageNode.user_id == proof.prover_user_id,
                    UserStorageNode.status == "active"
                ).limit(1)
                node = (await db.execute(node_q)).scalar_one_or_none()
                if node:
                    node.verification_count += 1
                    node.reliability_score = Decimal(str(max(0.0, float(node.reliability_score) * 0.90)))

    await db.commit()"""

if search_text in content:
    content = content.replace(search_text, replace_text)
    with open(path, 'w') as f:
        f.write(content)
    print("Patch applied successfully")
else:
    print("Search text not found")
