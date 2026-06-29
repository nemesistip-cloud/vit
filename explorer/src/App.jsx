import React, { Suspense, lazy } from 'react';
import { Route, Switch, Link, Router } from 'wouter';
import { Search, Menu, Box, LayoutDashboard, Globe, Zap } from 'lucide-react';
import ChainStats from './components/ChainStats';
import BlockList from './components/BlockList';

// Lazy load detail components for route-based code splitting
const BlockDetail = lazy(() => import('./components/BlockDetail'));
const TransactionDetail = lazy(() => import('./components/TransactionDetail'));
const AccountDetail = lazy(() => import('./components/AccountDetail'));
const NodeMap = lazy(() => import('./components/NodeMap'));

const LoadingFallback = () => (
    <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
    </div>
);

export default function App() {
  return (
    <Router base="/explorer">
    <div className="min-h-screen bg-[#0A0E1A] text-gray-200 font-Outfit">
      {/* Header */}
      <header className="border-b border-[#1F2937] bg-[#0A0E1A]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <div className="bg-green-500 p-1.5 rounded-lg">
                <Zap size={20} className="text-black fill-current" />
            </div>
            <span className="font-BarlowCondensed font-bold text-xl tracking-tight text-white uppercase">VIT <span className="text-green-500">Explorer</span></span>
          </Link>

          <div className="hidden md:flex flex-1 max-w-xl mx-8 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
            <input
              type="text"
              placeholder="Search by address / hash / block height..."
              className="w-full bg-[#121826] border border-[#1F2937] rounded-full py-2 pl-10 pr-4 text-sm focus:outline-none focus:border-purple-500 transition-colors"
            />
          </div>

          <nav className="flex items-center space-x-6">
            <Link href="/blocks" className="text-sm font-BarlowCondensed font-bold uppercase tracking-wider hover:text-green-500 transition-colors">Blocks</Link>
            <Link href="/nodes" className="text-sm font-BarlowCondensed font-bold uppercase tracking-wider hover:text-green-500 transition-colors">Network</Link>
            <button className="md:hidden text-gray-400"><Menu /></button>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 min-h-[70vh]">
        <Suspense fallback={<LoadingFallback />}>
        <Switch>
          <Route path="/">
            <div className="space-y-8">
              <ChainStats />
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                  <BlockList />
                </div>
                <div className="space-y-8">
                  <NodeMap />
                  <div className="bg-[#121826] border border-[#1F2937] rounded-lg p-6">
                      <h3 className="font-BarlowCondensed font-bold text-lg mb-4 text-white">SYSTEM STATUS</h3>
                      <div className="space-y-4">
                          <StatusRow label="Mainnet" status="Operational" color="text-green-500" />
                          <StatusRow label="P2P Gossip" status="Active" color="text-green-500" />
                          <StatusRow label="Tachyon Swarm" status="Healthy" color="text-green-500" />
                          <StatusRow label="Explorer Indexer" status="Live" color="text-purple-400" />
                      </div>
                  </div>
                </div>
              </div>
            </div>
          </Route>

          <Route path="/block/:id" component={BlockDetail} />
          <Route path="/tx/:hash" component={TransactionDetail} />
          <Route path="/account/:address" component={AccountDetail} />
          <Route path="/blocks">
              <div className="space-y-6">
                  <h1 className="text-2xl font-BarlowCondensed font-bold text-white uppercase tracking-tight">Chain Ledger</h1>
                  <BlockList />
              </div>
          </Route>
          <Route path="/nodes">
              <div className="space-y-6">
                  <h1 className="text-2xl font-BarlowCondensed font-bold text-white uppercase tracking-tight">Network Topology</h1>
                  <NodeMap />
                  <div className="bg-[#121826] border border-[#1F2937] rounded-lg p-6 text-center text-gray-500 italic">
                      Detailed node list coming in Session 8.4
                  </div>
              </div>
          </Route>

          <Route>
            <div className="text-center py-20">
              <h2 className="text-4xl font-BarlowCondensed font-bold mb-4">404 - DATA NOT FOUND</h2>
              <p className="text-gray-500 mb-8">The requested chain entity does not exist in the VIT Network index.</p>
              <Link href="/" className="bg-green-500 text-black px-6 py-2 rounded-full font-bold uppercase tracking-wider hover:bg-green-400 transition-colors">Return to Terminal</Link>
            </div>
          </Route>
        </Switch>
        </Suspense>
      </main>

      <footer className="border-t border-[#1F2937] py-8 mt-20">
          <div className="container mx-auto px-4 text-center">
              <p className="text-gray-600 text-xs font-BarlowCondensed tracking-[0.2em] uppercase">VIT Network v5.5.0 • Block Explorer Terminal</p>
          </div>
      </footer>
    </div>
    </Router>
  );
}

function StatusRow({ label, status, color }) {
    return (
        <div className="flex justify-between items-center text-xs font-BarlowCondensed">
            <span className="text-gray-500 uppercase tracking-widest">{label}</span>
            <span className={`${color} font-bold uppercase`}>{status}</span>
        </div>
    )
}
