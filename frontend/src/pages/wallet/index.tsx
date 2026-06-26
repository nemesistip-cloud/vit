import React, { Suspense } from "react";
import { Switch, Route } from "wouter";
import { WalletLayout } from "./WalletLayout";
import { WalletOverview } from "./WalletOverview";
import { WalletDeposit } from "./WalletDeposit";
import { WalletWithdraw } from "./WalletWithdraw";
import { VITCoinBuySell } from "./VITCoinBuySell";
import { CurrencyConvert } from "./CurrencyConvert";
import { StakingPage } from "./StakingPage";
import { SavingsVaults } from "./SavingsVaults";
import { P2PExchange } from "./P2PExchange";
import { BridgePage } from "./BridgePage";
import { TransactionHistory } from "./TransactionHistory";

function Loading() {
  return (
    <div className="flex items-center justify-center py-24">
      <div className="w-8 h-8 border-2 border-[#00E676]/20 border-t-[#00E676] rounded-full animate-spin" />
    </div>
  );
}

export default function WalletRoot() {
  return (
    <WalletLayout>
      <Suspense fallback={<Loading />}>
        <Switch>
          <Route path="/wallet/deposit" component={WalletDeposit} />
          <Route path="/wallet/withdraw" component={WalletWithdraw} />
          <Route path="/wallet/buy-sell" component={VITCoinBuySell} />
          <Route path="/wallet/convert" component={CurrencyConvert} />
          <Route path="/wallet/stake" component={StakingPage} />
          <Route path="/wallet/vaults" component={SavingsVaults} />
          <Route path="/wallet/p2p" component={P2PExchange} />
          <Route path="/wallet/bridge" component={BridgePage} />
          <Route path="/wallet/history" component={TransactionHistory} />
          <Route component={WalletOverview} />
        </Switch>
      </Suspense>
    </WalletLayout>
  );
}
