#!/usr/bin/env python3
"""Auto-payout USDC on Base - min 5 contributions"""
import json, hashlib
from web3 import Web3

RPC_URL = "https://mainnet.base.org"
import os
from dotenv import load_dotenv
load_dotenv("/app/.env")
PRIVATE_KEY = os.getenv("PAYOUT_PRIVATE_KEY")
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
REWARDS_FILE = "/app/data/rewards.json"
INDEX_FILE = "/app/data/index.json"
AGENTS_FILE = "/app/data/agents.json"
MIN_CONTRIBUTIONS = 5

USDC_ABI = [
    {"inputs":[{"name":"to","type":"address"},{"name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function","stateMutability":"nonpayable"},
    {"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function","stateMutability":"view"}
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
usdc = w3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)

def load_json(f):
    with open(f) as file: return json.load(file)

def save_json(f, d):
    with open(f, 'w') as file: json.dump(d, file)

def get_agent_num(agent_id, agents):
    # agent_id might already be the hash key in agents.json
    if agent_id in agents:
        return agents[agent_id]
    # or it might be the original id that needs hashing
    h = hashlib.sha256(agent_id.encode()).hexdigest()
    return agents.get(h, 0)

def send_usdc(to, amount_usd):
    amount = int(amount_usd * 1_000_000)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = usdc.functions.transfer(to, amount).build_transaction({
        'from': account.address, 'nonce': nonce, 'gas': 100000,
        'maxFeePerGas': w3.to_wei(0.1, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(0.05, 'gwei'),
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  TX: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return receipt.status == 1

def process_payouts():
    rewards = load_json(REWARDS_FILE)
    index = load_json(INDEX_FILE)
    agents = load_json(AGENTS_FILE)
    
    wallets = rewards.get("wallets", {})
    claims = rewards.get("claims", {})
    entries = index.get("entries", [])
    
    if not wallets:
        print("No wallets registered")
        return
    
    paid = 0
    for agent_id, wallet in wallets.items():
        agent_num = get_agent_num(agent_id, agents)
        contribs = len([e for e in entries if e.get("agent_num") == agent_num])
        
        if contribs < MIN_CONTRIBUTIONS:
            print(f"{agent_id}: {contribs} contribs (need {MIN_CONTRIBUTIONS})")
            continue
        
        earned = contribs * 2
        already_claimed = claims.get(agent_id, 0)
        available = earned - already_claimed
        
        if available <= 0:
            continue
        
        print(f"\n{agent_id}: {contribs} contribs, ${available} -> {wallet[:10]}...")
        try:
            if send_usdc(wallet, available):
                print(f"  OK!")
                claims[agent_id] = earned
                paid += 1
            else:
                print(f"  FAIL")
        except Exception as e:
            print(f"  ERR: {e}")
    
    rewards["claims"] = claims
    rewards["pending"] = []  # Clear pending, we auto-pay now
    save_json(REWARDS_FILE, rewards)
    print(f"\nDone! {paid} agents paid")

if __name__ == "__main__":
    print("=== UPLOADE Auto Payout ===")
    print(f"Wallet: {account.address}")
    print(f"Min contributions: {MIN_CONTRIBUTIONS}")
    balance = usdc.functions.balanceOf(account.address).call()
    print(f"USDC: ${balance / 1_000_000:.2f}")
    process_payouts()
