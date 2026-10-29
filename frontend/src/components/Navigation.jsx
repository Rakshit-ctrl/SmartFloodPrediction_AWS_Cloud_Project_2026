import { useEffect, useState } from 'react';
import { Waves } from 'lucide-react';

export const SECTIONS = [
  ['overview', 'Overview'],
  ['satellite', 'Satellite analysis'],
  ['history', 'Prediction history'],
  ['alerts', 'Alert rules'],
];

export function useActiveSection() {
  const read = () => window.location.hash.slice(1) || 'overview';
  const [active, setActive] = useState(read);
  useEffect(() => {
    const onHash = () => setActive(read());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  return active;
}

function Links({ active }) {
  return SECTIONS.map(([id, label]) => (
    <a key={id} href={`#${id}`} className={active === id ? 'active' : ''} aria-current={active === id ? 'page' : undefined}>
      {label}
    </a>
  ));
}

export function Sidebar({ online, active }) {
  return (
    <aside>
      <div className="logo">
        <Waves aria-hidden="true" />
        <div>
          <b>FloodSignal</b>
          <small>CLIMATE INTELLIGENCE</small>
        </div>
      </div>
      <nav aria-label="Primary">
        <p className="muted">WORKSPACE</p>
        <Links active={active} />
      </nav>
      <div className="sidebottom" role="status">
        <span className={online ? 'dot' : 'dot off'} aria-hidden="true" />
        {online ? 'API connected' : 'API disconnected'}
        <small>Prototype build · v0.2.0</small>
      </div>
    </aside>
  );
}

/** Shown instead of the sidebar on narrow screens. */
export function MobileNav({ active }) {
  return (
    <nav className="mobilenav" aria-label="Sections">
      <Links active={active} />
    </nav>
  );
}
