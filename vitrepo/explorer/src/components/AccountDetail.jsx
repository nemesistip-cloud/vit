import React, { useState, useEffect } from 'react';
import { useRoute } from 'wouter';
import { explorerApi } from '../api/client';
import { Wallet, ArrowUpRight, ArrowDownLeft, Database, Clock, Shield, User } from 'lucide-react';
import { Link } from 'wouter';

export default function AccountDetail() {
  const [, params] = useRoute("/account/:address");
  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const addr = params.address;
    Promise.all([
      explorerApi.getAccount(addr),
      explorerApi.getAccountTransactions(addr)
    ]).then(([accData, txData]) => {
      setAccount(accData);
      setTransactions(txData);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, [params.address]);

  if (loading) return <div className="text-white animate-pulse">Loading account profile...</div>;
  if (!account) return <div className="text-red-500 text-center py-12">Account not found in chain index</div>;

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
            <div className="flex items-center space-x-2 text-gray-500 mb-1">
                <User size={14} />
                <span className="text-[10px] uppercase tracking-[0.2em] font-BarlowCondensed">Account Identity</span>
            </div>
            <h1 className="text-xl md:text-3xl font-mono font-bold text-white break-all">{account.address}</h1>
        </div>
        {account.node_type && (
            <div className={`px-4 py-1 rounded border font-BarlowCondensed font-bold uppercase tracking-wider text-sm ${account.node_type === 'validator' ? 'bg-purple-500/10 border-purple-500/30 text-purple-400' : 'bg-green-500/10 border-green-500/30 text-green-400'}`}>
                {account.node_type} Node
            </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <BalanceCard label="Available Balance" value={account.balance} unit="VIT" color="text-green-500" />
        <BalanceCard label="Staked Balance" value={account.staked} unit="VIT" color="text-purple-500" />
        <BalanceCard label="Total Transactions" value={account.tx_count} unit="TXs" color="text-blue-400" />
        <BalanceCard label="Nonce" value={account.nonce} unit="" color="text-yellow-500" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-[#121826] border border-[#1F2937] rounded-lg p-6 space-y-4">
              <h3 className="text-gray-400 font-BarlowCondensed font-bold uppercase tracking-widest text-xs border-b border-[#1F2937] pb-3 mb-4">Chain Metadata</h3>
              <div className="flex justify-between items-center">
                  <span className="text-gray-500 text-xs">First Seen</span>
                  <Link href={`/block/${account.first_seen}`} className="text-white font-mono text-xs hover:underline">Block #{account.first_seen}</Link>
              </div>
              <div className="flex justify-between items-center">
                  <span className="text-gray-500 text-xs">Last Active</span>
                  <Link href={`/block/${account.last_active}`} className="text-white font-mono text-xs hover:underline">Block #{account.last_active}</Link>
              </div>
          </div>
      </div>

      <div className="bg-[#121826] border border-[#1F2937] rounded-lg overflow-hidden">
        <div className="p-4 border-b border-[#1F2937]">
          <h2 className="text-white font-BarlowCondensed font-bold text-xl uppercase">Activity History</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-[#0A0E1A] text-gray-400 text-xs uppercase font-BarlowCondensed">
              <tr>
                <th className="p-4 w-12"></th>
                <th className="p-4">Hash</th>
                <th className="p-4">Opposite Address</th>
                <th className="p-4">Value</th>
                <th className="p-4 text-right">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {transactions.map((tx) => {
                const isOut = tx.from_address === account.address;
                const opposite = isOut ? tx.to_address : tx.from_address;

                return (
                  <tr key={tx.hash} className="hover:bg-[#1F2937]/50 transition-colors text-xs font-mono">
                    <td className="p-4">
                        {isOut ? <ArrowUpRight size={14} className="text-red-400" /> : <ArrowDownLeft size={14} className="text-green-400" />}
                    </td>
                    <td className="p-4">
                      <Link href={`/tx/${tx.hash}`} className="text-purple-400 hover:underline">
                        {tx.hash.substring(0, 10)}...
                      </Link>
                    </td>
                    <td className="p-4 text-gray-400">
                      <Link href={`/account/${opposite}`} className="hover:text-white transition-colors">
                        {opposite.substring(0, 12)}...{opposite.substring(opposite.length - 8)}
                      </Link>
                    </td>
                    <td className={`p-4 font-bold ${isOut ? 'text-gray-300' : 'text-green-500'}`}>
                      {isOut ? '-' : '+'}{tx.amount.toFixed(4)} VIT
                    </td>
                    <td className="p-4 text-right text-gray-500">
                      {new Date(tx.timestamp * 1000).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {transactions.length === 0 && (
              <div className="p-12 text-center text-gray-500 italic">No transactions found for this account.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function BalanceCard({ label, value, unit, color }) {
    return (
        <div className="bg-[#121826] border border-[#1F2937] p-4 rounded-lg">
            <p className="text-gray-500 text-[10px] uppercase tracking-widest font-BarlowCondensed mb-2">{label}</p>
            <div className="flex items-baseline space-x-1">
                <span className={`text-xl font-bold font-mono ${color}`}>{typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 8 }) : value}</span>
                <span className="text-[10px] text-gray-500 font-bold">{unit}</span>
            </div>
        </div>
    )
}
