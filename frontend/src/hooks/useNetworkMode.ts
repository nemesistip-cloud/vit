import { useState, useEffect } from 'react';

interface NetworkConnection extends EventTarget {
  effectiveType?: string;
  saveData?: boolean;
  addEventListener(type: string, listener: EventListenerOrEventListenerObject, options?: boolean | AddEventListenerOptions): void;
  removeEventListener(type: string, listener: EventListenerOrEventListenerObject, options?: boolean | EventListenerOptions): void;
}

interface NavigatorWithConnection extends Navigator {
  connection?: NetworkConnection;
  mozConnection?: NetworkConnection;
  webkitConnection?: NetworkConnection;
}

export function useNetworkMode() {
  const [isDataLite, setIsDataLite] = useState(false);

  useEffect(() => {
    const nav = navigator as NavigatorWithConnection;
    const conn = nav.connection || nav.mozConnection || nav.webkitConnection;
    if (conn) {
      const checkNetwork = () => {
        const slowTypes = ['slow-2g', '2g', '3g'];
        setIsDataLite(slowTypes.includes(conn.effectiveType || '') || !!conn.saveData);
      };
      checkNetwork();
      conn.addEventListener('change', checkNetwork);
      return () => conn.removeEventListener('change', checkNetwork);
    }
  }, []);

  return { isDataLite };
}
