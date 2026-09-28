"""
Pre-seeded realistic enterprise deals for DealMind.
Populates Hindsight memory with realistic multi-call B2B sales cycles
so the user and judges can immediately see memory in action.
"""

from memory_engine import HindsightMemoryEngine

SAMPLE_DEALS = {
    "apex-logistics": {
        "name": "Apex Logistics Solutions",
        "value": "$65,000 ARR",
        "stage": "Proposal Review",
        "industry": "Supply Chain & Freight",
        "calls": [
            {
                "call_type": "Discovery Call (Call 1)",
                "date": "2026-09-02",
                "notes": (
                    "Initial meeting with Sarah Jenkins (CFO) and Mike Ramirez (VP of Operations). "
                    "Their legacy dispatch system causes 4-hour routing delays per day. "
                    "CRITICAL OBJECTION: Sarah stated they have an ironclad budget freeze until Q4. "
                    "She explicitly said: 'We cannot commit to upfront annual contracts right now, "
                    "any deal requiring immediate cash outlay will be vetoed by the board.'"
                ),
                "tags": ["objection:budget", "stakeholder:cfo", "pain:latency"]
            },
            {
                "call_type": "Technical Evaluation (Call 2)",
                "date": "2026-09-14",
                "notes": (
                    "Met Dave Miller (Lead Solutions Architect) and Engineering team. "
                    "Their current stack runs on Amazon EKS (Kubernetes) and self-hosted PostgreSQL. "
                    "Dave's major concern is proprietary vendor lock-in; he refuses black-box SaaS without open APIs. "
                    "COMPETITOR ALERT: Dave disclosed that CloudX sent a $15,000 quote yesterday and offered free migration help. "
                    "However, CloudX's API has rate-limiting issues Dave dislikes."
                ),
                "tags": ["competitor:cloudx", "tech:kubernetes", "objection:lock-in"]
            },
            {
                "call_type": "Security & Architecture Review (Call 3)",
                "date": "2026-09-22",
                "notes": (
                    "Compliance sync with Elena Rostova (Chief Information Security Officer). "
                    "Security requirements: SOC-2 Type II certificate, encrypted backups, and SSO (Okta integration). "
                    "Mike mentioned off the record that their team loves our workflow, but reminded us: "
                    "'Sarah will kill this deal next Monday unless we give them deferred Q4 billing and beat CloudX on migration.'"
                ),
                "tags": ["security:soc2", "stakeholder:ciso", "closing_factor:deferred_billing"]
            }
        ]
    },
    "fintech-global": {
        "name": "FinTech Global Payments",
        "value": "$120,000 ARR",
        "stage": "Vendor Comparison",
        "industry": "Financial Services",
        "calls": [
            {
                "call_type": "Discovery (Call 1)",
                "date": "2026-09-05",
                "notes": (
                    "Met with Alex Vance (Head of Payments). High chargeback rates on international card processing. "
                    "Strict requirement: API response times must be strictly under 45ms. "
                    "Alex got burned by their previous vendor whose service crashed during Black Friday."
                ),
                "tags": ["latency:45ms", "pain:chargebacks", "risk:uptime"]
            },
            {
                "call_type": "Competitive Bake-off (Call 2)",
                "date": "2026-09-18",
                "notes": (
                    "Alex revealed they are actively testing Stripe Radar and DataVisor. "
                    "DataVisor offered a 20% discount on transaction volume. "
                    "Alex expressed frustration with DataVisor's false-positive rate blocking legitimate customers."
                ),
                "tags": ["competitor:datavisor", "competitor:stripe", "objection:false_positives"]
            }
        ]
    }
}


def seed_hindsight_memory(engine: HindsightMemoryEngine, force_reset: bool = False):
    """
    Populates Hindsight memory banks with realistic historical calls.
    """
    for deal_id, deal_info in SAMPLE_DEALS.items():
        existing = engine.get_all_memories(deal_id)
        if existing and not force_reset:
            continue

        if force_reset:
            engine.reset_bank(deal_id)

        print(f"[Seed] Seeding Hindsight memory bank for {deal_info['name']}...")
        for call in deal_info["calls"]:
            content = f"[{call['call_type']} - Date: {call['date']}] {call['notes']}"
            metadata = {
                "deal_name": deal_info["name"],
                "deal_id": deal_id,
                "deal_value": deal_info["value"],
                "call_type": call["call_type"],
                "date": call["date"],
                "tags": call["tags"]
            }
            engine.retain(bank_id=deal_id, content=content, metadata=metadata)

    print("[Seed] Hindsight memory seeding complete!")


if __name__ == "__main__":
    engine = HindsightMemoryEngine()
    seed_hindsight_memory(engine, force_reset=True)
