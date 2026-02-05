import json

# Load index
with open('/app/data/index.json') as f:
    data = json.load(f)

# Count per agent
agent_counts = {}
for entry in data['entries']:
    agent = entry.get('agent_num', entry.get('agent_id', 'unknown'))
    agent_counts[agent] = agent_counts.get(agent, 0) + 1

# Sort by count
sorted_agents = sorted(agent_counts.items(), key=lambda x: -x[1])

print("=== AGENT CONTRIBUTION STATS ===\n")
print(f"{'Agent':<15} {'Experiences':<12} {'Payout ($2 each)'}")
print("-" * 45)

total = 0
for agent, count in sorted_agents:
    payout = count * 2
    total += payout
    print(f"Agent {agent:<9} {count:<12} ${payout}")

print("-" * 45)
print(f"{'TOTAL':<15} {len(data['entries']):<12} ${total}")
