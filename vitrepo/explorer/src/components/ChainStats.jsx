import React, { useState, useEffect } from 'react';
import { explorerApi } from '../api/client';
import { Database, Activity, Server, Clock, Coins } from 'lucide-react';

const StatCard = ({ icon: Icon, label, value, color }) => (
  <div className="bg-[#121826] border border-[#1F2937] p-4 rounded-lg flex items-center space-x-4">
    <div className={`p-3 rounded-full bg-opacity-10 ${color}`}>
      <Icon size={20} className={color.replace('bg-', 'text-')} />
    </div>
    <div>
      <p className="text-gray-400 text-xs uppercase font-BarlowCondensed tracking-wider">{label}</p>
      <p className="text-white font-BarlowCondensed text-lg font-bold">{value}</p>
    </div>
  </div>
);

export default function ChainStats() {
  const [stats, setStats] = useState({
    latestBlock: 0,
    totalTxs: 0,
    activeNodes: 0,
    avgBlockTime: "15s",
    circulation: "0 VIT"
  });

  const fetchStats = async () => {
    try {
      const data = await explorerApi.getStats();

      setStats({
        latestBlock: data.latest_block_height,
        totalTxs: data.total_transactions,
        activeNodes: data.total_nodes || data.active_nodes || 0,
        avgBlockTime: `${data.avg_block_time_seconds}s`,
        circulation: `${parseFloat(data.total_vit_in_circulation).toLocaleString()} VIT`
      });
    } catch (err) {
      console.error("Failed to fetch stats", err);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
      <StatCard icon={Database} label="Latest Block" value={`#${stats.latestBlock}`} color="bg-green-500" />
      <StatCard icon={Activity} label="Total Transactions" value={stats.totalTxs} color="bg-purple-500" />
      <StatCard icon={Server} label="Active Nodes" value={stats.activeNodes} color="bg-blue-500" />
      <StatCard icon={Clock} label="Avg Block Time" value={stats.avgBlockTime} color="bg-yellow-500" />
      <StatCard icon={Coins} label="Circulation" value={stats.circulation} color="bg-green-500" />
    </div>
  );
}
