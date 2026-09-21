# VIT Node — Setup Guide

## Requirements
- Python 3.10+
- Google account (for Drive storage)
- 10GB+ available storage

## Install (2 minutes)
pip install vit-node  (or: pip install -e . from repo)

## Setup
vit-node setup
  → Creates keystore (you set a password)
  → Connects Google Drive (OAuth browser popup)
  → Registers with VIT Network
  → Starts earning VITCoin

## Commands
vit-node start     — Start the node daemon
vit-node stop      — Stop gracefully
vit-node status    — Show earnings, shards held, uptime
vit-node earnings  — Detailed VITCoin earnings history
vit-node logs      — Tail node logs
