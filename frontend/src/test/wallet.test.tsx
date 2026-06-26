import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { WalletBalanceCard } from "../components/wallet/WalletBalanceCard";
import { TransactionRow } from "../components/wallet/TransactionRow";
import React from "react";

// Mock date-fns
vi.mock("date-fns", () => ({
  formatDistanceToNow: () => "just now",
}));

describe("WalletBalanceCard", () => {
  it("renders amount correctly", () => {
    render(<WalletBalanceCard label="VIT" amount={100} symbol="VIT" />);
    expect(screen.getByText("100.00")).toBeDefined();
  });

  it("shows Add CTA for zero balance", () => {
    render(<WalletBalanceCard label="VIT" amount={0} symbol="VIT" />);
    expect(screen.getByText(/Add VIT/i)).toBeDefined();
  });

  it("hides subLabel when subAmount is 0", () => {
    const { queryByText } = render(
      <WalletBalanceCard label="VIT" amount={100} subLabel="Daily est." subAmount={0} />
    );
    expect(queryByText("Daily est.")).toBeNull();
  });
});

describe("TransactionRow", () => {
  const tx = {
    id: "tx1",
    type: "deposit",
    amount: 100,
    currency: "VITCoin",
    status: "confirmed",
    direction: "credit",
    created_at: new Date().toISOString(),
  } as any;

  it("renders status labels correctly", () => {
    render(<TransactionRow tx={tx} />);
    expect(screen.getByText("confirmed")).toBeDefined();
  });

  it("renders processing for pending status", () => {
    render(<TransactionRow tx={{ ...tx, status: "pending" }} />);
    expect(screen.getByText(/Processing.../i)).toBeDefined();
  });
});
