import React, { useState, useEffect } from 'react';
import { Link } from 'wouter';
import { explorerApi } from '../api/client';
import { formatDistanceToNow } from 'date-fns';
import { Box, Hash, User, Gift, Terminal } from 'lucide-react';

export default function BlockList() {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    explorerApi.getBlocks(20).then(data => {
      setBlocks(data);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="animate-pulse space-y-4">
      {[...Array(10)].map((_, i) => (
          <div key={i} className="h-16 bg-[#121826] rounded-lg"></div>
      ))}
  </div>;

  return (
    <div className="bg-[#121826] border border-[#1F2937] rounded-lg overflow-hidden">
      <div className="p-4 border-b border-[#1F2937] flex items-center justify-between">
        <h2 className="text-white font-BarlowCondensed font-bold text-xl flex items-center">
            <Box size={20} className="mr-2 text-green-500" />
            Recent Blocks
        </h2>
        <Link href="/blocks" className="text-purple-500 text-sm hover:underline font-BarlowCondensed">View All</Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-[#0A0E1A] text-gray-400 text-xs uppercase font-BarlowCondensed">
            <tr>
              <th className="p-4">Height</th>
              <th className="p-4">Hash</th>
              <th className="p-4">TXs</th>
              <th className="p-4">Validator</th>
              <th className="p-4">Reward</th>
              <th className="p-4 text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1F2937]">
            {blocks.map((b) => (
              <tr key={b.hash} className="hover:bg-[#1F2937]/50 transition-colors">
                <td className="p-4">
                  <Link href={`/block/${b.height}`} className="text-green-500 font-bold">#{b.height}</Link>
                </td>
                <td className="p-4 text-gray-300 font-mono text-xs">
                  {b.hash.substring(0, 10)}...{b.hash.substring(b.hash.length - 8)}
                </td>
                <td className="p-4 text-gray-300">
                    <span className="bg-[#0A0E1A] px-2 py-1 rounded text-xs border border-[#1F2937] flex items-center w-fit">
                        <Terminal size={12} className="mr-1 text-purple-400" />
                        {b.tx_count}
                    </span>
                </td>
                <td className="p-4">
                    <Link href={`/account/${b.validator}`} className="text-purple-400 text-xs hover:underline flex items-center">
                        <User size={12} className="mr-1" />
                        {b.validator.substring(0, 8)}...
                    </Link>
                </td>
                <td className="p-4 text-green-500 text-xs font-bold font-mono">
                    <Gift size={12} className="inline mr-1" />
                    {b.block_reward.toFixed(4)} VIT
                </td>
                <td className="p-4 text-right text-gray-400 text-xs">
                  {formatDistanceToNow(new Date(b.timestamp * 1000), { addSuffix: true })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
