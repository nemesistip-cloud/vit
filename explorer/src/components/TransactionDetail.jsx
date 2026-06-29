import React, { useState, useEffect } from 'react';
import { useRoute } from 'wouter';
import { explorerApi } from '../api/client';
import { Hash, User, Clock, Terminal, Shield, Activity, ArrowRight } from 'lucide-react';
import { Link } from 'wouter';

export default function TransactionDetail() {
  const [, params] = useRoute("/tx/:hash");
  const [tx, setTx] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    explorerApi.getTransaction(params.hash).then(data => {
      setTx(data);
      setLoading(false);
    });
  }, [params.hash]);

  if (loading) return <div className="text-white animate-pulse">Loading transaction...</div>;
  if (!tx) return <div className="text-red-500">Transaction not found</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 mb-6">
        <Activity size={24} className="text-purple-500" />
        <h1 className="text-2xl font-BarlowCondensed font-bold text-white uppercase tracking-tight">Transaction Receipt</h1>
      </div>

      <div className="bg-[#121826] border border-[#1F2937] rounded-lg p-6 space-y-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1F2937] pb-6">
            <div>
                <p className="text-gray-500 text-[10px] uppercase tracking-widest mb-1">Transaction Hash</p>
                <p className="text-white font-mono text-sm break-all">{tx.hash}</p>
            </div>
            <div className="text-right">
                <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${tx.status === 'confirmed' ? 'bg-green-500/20 text-green-500 border border-green-500/30' : 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30'}`}>
                    {tx.status}
                </span>
            </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
                <DetailRow label="Block" value={`#${tx.block_height}`} isLink href={`/block/${tx.block_height}`} />
                <DetailRow label="Timestamp" value={new Date(tx.timestamp * 1000).toLocaleString()} />
                <DetailRow label="Nonce" value={tx.nonce} />
                <DetailRow label="Type" value={tx.type.toUpperCase()} />
            </div>
            <div className="space-y-4">
                <DetailRow label="Value" value={`${tx.amount.toFixed(8)} VIT`} isHighlighted />
                <DetailRow label="Gas Fee" value={`${tx.gas_fee.toFixed(8)} VIT`} />
            </div>
        </div>

        <div className="bg-[#0A0E1A] rounded-lg p-6 border border-[#1F2937] space-y-6">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6 text-center">
                <div className="flex-1 w-full">
                    <p className="text-gray-500 text-[10px] uppercase tracking-widest mb-2">From</p>
                    <Link href={`/account/${tx.from_address}`} className="text-purple-400 font-mono text-sm hover:underline break-all block">
                        {tx.from_address}
                    </Link>
                </div>
                <div className="bg-[#1F2937] p-2 rounded-full hidden md:block">
                    <ArrowRight size={16} className="text-gray-400" />
                </div>
                <div className="flex-1 w-full">
                    <p className="text-gray-500 text-[10px] uppercase tracking-widest mb-2">To</p>
                    <Link href={`/account/${tx.to_address}`} className="text-green-500 font-mono text-sm hover:underline break-all block">
                        {tx.to_address}
                    </Link>
                </div>
            </div>
        </div>

        <div className="space-y-2 pt-4">
            <p className="text-gray-500 text-[10px] uppercase tracking-widest">Signature</p>
            <div className="bg-[#0A0E1A] p-3 rounded font-mono text-[10px] text-gray-400 break-all border border-[#1F2937]">
                {tx.signature}
            </div>
        </div>

        {tx.data && Object.keys(tx.data).length > 0 && (
            <div className="space-y-2">
                <p className="text-gray-500 text-[10px] uppercase tracking-widest">Payload Data</p>
                <pre className="bg-[#0A0E1A] p-3 rounded font-mono text-xs text-green-500 border border-[#1F2937] overflow-x-auto">
                    {JSON.stringify(tx.data, null, 2)}
                </pre>
            </div>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value, isLink, href, isHighlighted }) {
    return (
        <div className="flex items-center justify-between py-2 border-b border-[#1F2937]/50 last:border-0">
            <span className="text-gray-500 text-xs font-BarlowCondensed uppercase tracking-wider">{label}</span>
            {isLink ? (
                <Link href={href} className="text-purple-400 text-xs font-mono hover:underline">{value}</Link>
            ) : (
                <span className={`text-xs font-mono ${isHighlighted ? 'text-green-500 font-bold' : 'text-gray-300'}`}>{value}</span>
            )}
        </div>
    )
}
