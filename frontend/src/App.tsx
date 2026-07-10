import { Routes, Route } from 'react-router-dom'
import { Navbar } from '@/components/layout/Navbar'
import { Footer } from '@/components/layout/Footer'
import Home        from '@/pages/Home'
import Platform    from '@/pages/Platform'
import AI          from '@/pages/AI'
import Storage     from '@/pages/Storage'
import Status      from '@/pages/Status'
import Developers  from '@/pages/Developers'
import Documentation from '@/pages/Documentation'
import Roadmap     from '@/pages/Roadmap'
import About       from '@/pages/About'

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/"           element={<Home />} />
          <Route path="/platform"   element={<Platform />} />
          <Route path="/ai"         element={<AI />} />
          <Route path="/storage"    element={<Storage />} />
          <Route path="/status"     element={<Status />} />
          <Route path="/developers" element={<Developers />} />
          <Route path="/docs"       element={<Documentation />} />
          <Route path="/roadmap"    element={<Roadmap />} />
          <Route path="/about"      element={<About />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
