import React, { useState, useEffect } from 'react';
import { useRoute } from 'wouter';
import { explorerApi } from '../api/client';
import { formatDistanceToNow } from 'date-fns';
import { Box, Hash, User, Gift, Terminal, Calendar, Layers, Link as LinkIcon } from 'lucide-react';
import { Link } from 'wouter';

export default function BlockDetail() {
  const [, params] = useRoute("/block/:id");
  const [block, setBlock] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    explorerApi.getBlock(params.id).then(data => {
      setBlock(data);
      setLoading(false);
    });
  }, [params.id]);

  if (loading) return <div className="text-white animate-pulse">Loading block details...</div>;
  if (!block) return <div className="text-red-500">Block not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <Link href="/" className="text-gray-400 hover:text-white transition-colors">
          <Layers size={24} />
        </Link>
        <h1 className="text-2xl font-BarlowCondensed font-bold text-white">Block #{block.height}</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#121826] border border-[#1F2937] rounded-lg p-6 space-y-4">
          <DetailItem icon={Hash} label="Block Hash" value={block.hash} isMono />
          <DetailItem icon={LinkIcon} label="Previous Hash" value={block.prev_hash} isMono />
          <DetailItem icon={Calendar} label="Timestamp" value={new Date(block.timestamp * 1000).toLocaleString()} />
          <DetailItem icon={User} label="Validator" value={block.validator} isLink href={`/account/${block.validator}`} />
        </div>
        <div className="bg-[#121826] border border-[#1F2937] rounded-lg p-6 space-y-4">
          <DetailItem icon={Gift} label="Block Reward" value={`${block.block_reward.toFixed(8)} VIT`} />
          <DetailItem icon={Terminal} label="Transaction Count" value={block.tx_count} />
          <DetailItem icon={Terminal} label="Total Fees" value={`${block.total_fees.toFixed(8)} VIT`} />
        </div>
      </div>

      <div className="bg-[#121826] border border-[#1F2937] rounded-lg overflow-hidden">
        <div className="p-4 border-b border-[#1F2937]">
          <h2 className="text-white font-BarlowCondensed font-bold text-xl">Transactions ({block.transactions.length})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-[#0A0E1A] text-gray-400 text-xs uppercase font-BarlowCondensed">
              <tr>
                <th className="p-4">TX Hash</th>
                <th className="p-4">From</th>
                <th className="p-4">To</th>
                <th className="p-4">Amount</th>
                <th className="p-4 text-right">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {block.transactions.map((tx) => (
                <tr key={tx.hash} className="hover:bg-[#1F2937]/50 transition-colors">
                  <td className="p-4">
                    <Link href={`/tx/${tx.hash}`} className="text-purple-400 font-mono text-xs hover:underline">
                      {tx.hash.substring(0, 12)}...
                    </Link>
                  </td>
                  <td className="p-4 text-gray-400 font-mono text-xs">
                    <Link href={`/account/${tx.from}`} className="hover:text-white">{tx.from.substring(0, 10)}...</Link>
                  </td>
                  <td className="p-4 text-gray-400 font-mono text-xs">
                    <Link href={`/account/${tx.to}`} className="hover:text-white">{tx.to.substring(0, 10)}...</Link>
                  </td>
                  <td className="p-4 text-green-500 font-bold font-mono text-xs">
                    {tx.amount.toFixed(4)} VIT
                  </td>
                  <td className="p-4 text-right">
                    <span className="bg-[#0A0E1A] px-2 py-1 rounded text-[10px] border border-[#1F2937] text-gray-400 uppercase">
                      {tx.type}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function DetailItem({ icon: Icon, label, value, isMono, isLink, href }) {
  return (
    <div className="flex items-start space-x-3">
      <div className="mt-1 text-gray-500"><Icon size={16} /></div>
      <div className="flex-1 min-w-0">
        <p className="text-gray-500 text-[10px] uppercase tracking-widest font-BarlowCondensed">{label}</p>
        {isLink ? (
          <Link href={href} className="text-purple-400 hover:text-purple-300 font-mono text-xs truncate block">{value}</Link>
        ) : (
          <p className={`text-gray-200 text-xs truncate block ${isMono ? 'font-mono' : ''}`}>{value}</p>
        )}
      </div>
    </div>
  );
}
