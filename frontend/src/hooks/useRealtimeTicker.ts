import { useEffect, useState } from 'react';
import { db } from '@/lib/firebase';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!db) {
      setLoading(false);
      return;
    }

    let unsub: (() => void) | undefined;

    import('firebase/firestore').then(({ doc, onSnapshot }) => {
      unsub = onSnapshot(
        doc(db!, 'system', 'ticker'),
        (snapshot) => {
          if (snapshot.exists()) {
            setData(snapshot.data() as TickerData);
          }
          setLoading(false);
        },
        (err) => {
          console.warn("Firestore ticker subscription error:", err);
          setError(err);
          setLoading(false);
        }
      );
    }).catch(() => {
      setLoading(false);
    });

    return () => unsub?.();
  }, []);

  return { data, loading, error };
}
