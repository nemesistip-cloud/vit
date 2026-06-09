from decimal import Decimal

def calculate_price(rolling_revenue, total_collateral, circulating_supply):
    annualized_revenue = rolling_revenue * Decimal("12")
    svi = circulating_supply / total_collateral if total_collateral > 0 else Decimal("1")
    svi_modifier = Decimal("1.0") / svi if svi > 0 else Decimal("1.0")

    raw_valuation = (annualized_revenue + total_collateral) / circulating_supply
    final_valuation = raw_valuation * svi_modifier
    return final_valuation

# Case 1: Revenue = 0, Collateral = 1000, Supply = 1000 (SVI = 1)
# Price should be 1.0
p1 = calculate_price(Decimal("0"), Decimal("1000"), Decimal("1000"))
print(f"Case 1: {p1}")

# Case 2: Revenue = 100/mo, Collateral = 1000, Supply = 1000 (SVI = 1)
# (1200 + 1000) / 1000 * 1 = 2.2
p2 = calculate_price(Decimal("100"), Decimal("1000"), Decimal("1000"))
print(f"Case 2: {p2}")

# Case 3: Revenue = 0, Collateral = 500, Supply = 1000 (SVI = 2)
# (0 + 500) / 1000 * 0.5 = 0.5 * 0.5 = 0.25
p3 = calculate_price(Decimal("0"), Decimal("500"), Decimal("1000"))
print(f"Case 3: {p3}")
