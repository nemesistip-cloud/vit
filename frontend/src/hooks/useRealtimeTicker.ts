import { useEffect, useState } from 'react';
import { db } from '@/lib/firebase';
import { doc, onSnapshot } from 'firebase/firestore';

export interface TickerData {
  vit_price?: number;
  change_24h?: number;
  total_users?: number;
  active_users_30d?: number;
  active_validators?: number;
  total_staked_vit?: number;
  total_predictions?: number;
  accuracy_rate?: number;
  last_updated?: any;
}

export function useRealtimeTicker() {
  const [data, setData] = useState<TickerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // We assume a 'system' collection and a 'stats' document
    const unsub = onSnapshot(
      doc(db, 'system', 'ticker'),
      (doc) => {
        if (doc.exists()) {
          setData(doc.data() as TickerData);
        }
        setLoading(false);
      },
      (err) => {
        console.error("Firestore ticker subscription error:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => unsub();
  }, []);

  return { data, loading, error };
}
