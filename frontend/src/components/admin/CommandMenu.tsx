import React, { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useLocation } from "wouter";
import {
  LayoutDashboard, Users, Wallet, Trophy, Shield, Brain,
  Store, Settings, FileText, Activity, Search
} from "lucide-react";

interface CommandMenuProps {
  open: boolean;
  setOpen: (open: boolean) => void;
}

export function CommandMenu({ open, setOpen }: CommandMenuProps) {
  const [, navigate] = useLocation();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(!open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, setOpen]);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Global Command Menu"
      className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[540px] bg-[#0b1018] rounded-sm border border-white/10 shadow-2xl z-[100] overflow-hidden font-['Outfit']"
    >
      <div className="flex items-center border-b border-white/5 px-4 py-3 gap-3">
        <Search size={16} className="text-white/20" />
        <Command.Input
          autoFocus
          placeholder="Type a command or search modules..."
          className="flex-1 bg-transparent border-none outline-none text-white text-sm placeholder:text-white/20"
        />
        <div className="px-1.5 py-0.5 rounded-sm bg-white/5 border border-white/10 text-[9px] font-bold text-white/30 uppercase tracking-widest">
          esc
        </div>
      </div>

      <Command.List className="max-h-[360px] overflow-y-auto p-2 scrollbar-none">
        <Command.Empty className="py-12 text-center text-xs text-white/20 font-medium uppercase tracking-widest">No matching operations found</Command.Empty>

        <Command.Group heading="Navigation" className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/20 px-3 py-2">
          <Item onSelect={() => runCommand(() => navigate("/admin"))} icon={LayoutDashboard}>Mission Control Dashboard</Item>
          <Item onSelect={() => runCommand(() => navigate("/admin/users"))} icon={Users}>Entity Intelligence Registry</Item>
          <Item onSelect={() => runCommand(() => navigate("/admin/wallet"))} icon={Wallet}>Treasury & Finance Operations</Item>
          <Item onSelect={() => runCommand(() => navigate("/admin/matches"))} icon={Trophy}>Market & Prediction Ledger</Item>
          <Item onSelect={() => runCommand(() => navigate("/admin/models"))} icon={Brain}>AI Operations Center</Item>
          <Item onSelect={() => runCommand(() => navigate("/admin/config"))} icon={Settings}>Platform Control Center</Item>
        </Command.Group>

        <Command.Group heading="System Operations" className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/20 px-3 py-2 mt-2">
          <Item onSelect={() => runCommand(() => navigate("/admin/audit"))} icon={FileText}>View Global Audit Ledger</Item>
          <Item onSelect={() => runCommand(() => navigate("/admin/system"))} icon={Activity}>System Infrastructure Health</Item>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}

function Item({ children, icon: Icon, onSelect }: { children: React.ReactNode; icon: any; onSelect?: () => void }) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex items-center gap-3 px-3 py-2.5 rounded-sm text-xs font-medium text-white/60 cursor-pointer hover:bg-white/5 aria-selected:bg-white/5 aria-selected:text-[#00E676] transition-all"
    >
      <Icon size={14} className="opacity-50" />
      <span>{children}</span>
    </Command.Item>
  );
}
