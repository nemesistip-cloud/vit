import { useEffect, useState } from 'react';
import { db } from '@/lib/firebase';
import type { Match } from '@/api-client/schemas';

export function useRealtimeMatches(limitCount: number = 50) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!db) {
      setLoading(false);
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
