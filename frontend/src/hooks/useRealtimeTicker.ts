import { useEffect, useState } from 'react';
import { db, isFirebaseConfigured } from '@/lib/firebase';
import { apiGet } from '@/lib/apiClient';

export interface TickerData {
  vit_price?: number;
  change_24h?: number;
  total_users?: number;
  active_users_30d?: number;
  active_validators?: number;
  total_staked_vit?: number;
  total_predictions?: number;
  accuracy_rate?: number;
  last_updated?: string | number | Date;
}

export function useRealtimeTicker() {
  const [data, setData] = useState<TickerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // F4: REST Fallback if Firebase not configured
    if (!isFirebaseConfigured || !db) {
      const fetchFallback = async () => {
        try {
          const res = await apiGet<any>('/api/dashboard/summary');
          const sys = await apiGet<any>('/api/system/status');
          const price = await apiGet<any>('/api/dashboard/vitcoin-price');

          setData({
            vit_price: price?.price_usd,
            change_24h: price?.change_24h,
            total_users: sys?.total_users,
            active_users_30d: sys?.active_users_30d,
            active_validators: sys?.active_validators,
            total_staked_vit: sys?.total_staked_vit,
            total_predictions: res?.total_predictions,
            accuracy_rate: res?.accuracy_rate,
            last_updated: new Date().toISOString()
          });
          setLoading(false);
        } catch (err: any) {
          setError(err);
          setLoading(false);
        }
      };
      fetchFallback();
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
