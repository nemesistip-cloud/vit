import { useEffect, useState } from 'react';
import { db, isFirebaseConfigured } from '@/lib/firebase';
import type { Match } from '@/api-client/schemas';
import { apiGet } from '@/lib/apiClient';

export function useRealtimeMatches(limitCount: number = 50) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // F3: REST Fallback if Firebase not configured
    if (!isFirebaseConfigured || !db) {
      const fetchFallback = async () => {
        try {
          const data = await apiGet<Match[]>(`/api/matches?limit=${limitCount}`);
          setMatches(data);
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

    import('firebase/firestore').then(({ collection, query, onSnapshot, limit, orderBy }) => {
      const q = query(
        collection(db!, 'matches'),
        orderBy('kickoff_time', 'desc'),
        limit(limitCount)
      );

      unsub = onSnapshot(
        q,
        (snapshot) => {
          const matchesData: Match[] = [];
          snapshot.forEach((doc) => {
            matchesData.push({ id: doc.id, ...doc.data() } as any);
          });
          setMatches(matchesData);
          setLoading(false);
        },
        (err) => {
          console.warn("Firestore matches subscription error:", err);
          setError(err);
          setLoading(false);
        }
      );
    }).catch(() => {
      setLoading(false);
    });

    return () => unsub?.();
  }, [limitCount]);

  return { matches, loading, error };
}
