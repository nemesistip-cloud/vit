# Value Intelligence Trust (VIT)

To build intelligent systems where value, trust, and merit become programmable.

VIT is an integrated ecosystem of AI, Blockchain, and autonomous infrastructure designed to coordinate economies more efficiently than corruption, manipulation, or chaos. This repository contains the core platform combining a 13-model ML ensemble, a multi-AI LLM cascade, a sovereign blockchain ledger (VIT-Chain), and a swarm of 22 autonomous agents.

## Design Philosophy

- **Institutional-Grade**: High-fidelity analysis and cryptographic transparency.
- **Programmable Trust**: Merit-based coordination via decentralized identity (DID).
- **Neural Connectivity**: Multi-provider AI consensus (DeepSeek, Claude, Grok, Gemini).
- **Premium Geometric**: A minimal, futurist design language built for precision.

## Core Layers

- **VIT Intelligence**: The AI backbone delivering predictive analytics and tactical insights.
- **VIT Chain**: A dedicated ledger for verifiable trust and settlement.
- **VIT Cloud**: Decentralized infrastructure for smart contract execution and storage.
- **VIT Network**: A swarm of 22 specialized agents governing platform health and performance.

## Getting Started

### Local Environment

1. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Set ADMIN_PASSWORD and JWT_SECRET_KEY in .env
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

3. **Start Services**:
   - Backend: `./scripts/start_backend.sh`
   - Frontend: `./scripts/start_frontend.sh`

### Configuration

The system uses a **Single Source of Truth** for branding. All platform names, taglines, and mission statements are centralized in `app/config.py` and propagated to the frontend via the Public Config API.

## Intelligence Training

The system supports local and cloud-based training:
- **Colab Pipeline**: Use `colab/train_real_match_models.py` for cloud-scale training.
- **Ensemble Registry**: Upload trained `.pkl` weights via the Admin Control Center.
- **Autonomous Tuning**: The `ModelTunerAgent` suggests parameter updates based on live performance metrics.

## Contributing

We are building the infrastructure for a digital civilization based on merit and verifiable trust. Contributors are expected to maintain the "Institutional-Grade" standards of the VIT Ecosystem.

---
© 2026 Value Intelligence Trust (VIT) · Where Value, Intelligence, and Trust Converge.
