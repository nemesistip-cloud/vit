import asyncio
from app.services.accumulator_service import AccumulatorService, AccumulatorLeg

async def test():
    svc = AccumulatorService()
    legs = [
        AccumulatorLeg(1, "A", "B", "home", 0.6, 2.0),
        AccumulatorLeg(2, "C", "D", "away", 0.5, 2.5),
        AccumulatorLeg(3, "E", "F", "draw", 0.4, 3.5),
    ]

    joint = svc.calculate_joint_probability(legs)
    odds = svc.calculate_combined_odds(legs)
    kelly = svc.calculate_kelly_stake(joint, odds)

    print(f"Joint Prob: {joint}")
    print(f"Total Odds: {odds}")
    print(f"Kelly Stake: {kelly}")

    # Expected: 0.6 * 0.5 * 0.4 = 0.12
    # Expected odds: 2.0 * 2.5 * 3.5 = 17.5
    assert joint == 0.12
    assert odds == 17.5
    print("Accumulator calculation logic OK")

if __name__ == "__main__":
    asyncio.run(test())
