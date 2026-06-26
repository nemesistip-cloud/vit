import { useEffect, useRef, useState } from "react";
import { useLocation } from "wouter";

export function RouteProgressBar() {
  const [location] = useLocation();
  const [width, setWidth] = useState(0);
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevLocation = useRef<string>(location);

  useEffect(() => {
    if (location === prevLocation.current) return;
    prevLocation.current = location;

    if (timerRef.current) clearTimeout(timerRef.current);

    setWidth(0);
    setVisible(true);

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setWidth(70);
      });
    });

    timerRef.current = setTimeout(() => {
      setWidth(100);
      setTimeout(() => {
        setVisible(false);
        setWidth(0);
      }, 300);
    }, 250);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [location]);

  if (!visible && width === 0) return null;

  return (
    <div
      className="fixed top-0 left-0 right-0 z-[9999] h-[2px] pointer-events-none"
      style={{ background: "transparent" }}
    >
      <div
        className="h-full bg-primary transition-all ease-out"
        style={{
          width: `${width}%`,
          transitionDuration: width === 100 ? "200ms" : "400ms",
          boxShadow: "0 0 8px var(--color-primary)",
        }}
      />
    </div>
  );
}
