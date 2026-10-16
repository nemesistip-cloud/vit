import { useState, useEffect } from 'react'

export type ViewportMode = 'mobile' | 'tablet' | 'desktop'

export function useViewport() {
  const [width, setWidth] = useState<number>(() => (typeof window !== 'undefined' ? window.innerWidth : 1200))

  useEffect(() => {
    if (typeof window === 'undefined') return
    const handleResize = () => setWidth(window.innerWidth)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const isMobile = width < 768
  const isTablet = width >= 768 && width < 1200
  const isDesktop = width >= 1200
  const mode: ViewportMode = isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop'

  return { width, isMobile, isTablet, isDesktop, mode }
}
