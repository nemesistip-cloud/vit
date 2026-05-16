import { useEffect, useState } from 'react';
import { db } from '@/lib/firebase';
import { collection, query, onSnapshot, limit, orderBy } from 'firebase/firestore';
import type { Match } from '@/api-client/schemas';

export function useRealtimeMatches(limitCount: number = 50) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const q = query(
      collection(db, 'matches'),
      orderBy('kickoff_time', 'desc'),
      limit(limitCount)
    );

    const unsub = onSnapshot(
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
        console.error("Firestore matches subscription error:", err);
        setError(err);
        setLoading(false);
      }
    );

    return () => unsub();
  }, [limitCount]);

  return { matches, loading, error };
}
