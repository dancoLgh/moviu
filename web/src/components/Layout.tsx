import { NavLink } from 'react-router-dom';
import './Layout.css';

const navLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/servicios', label: 'Servicios' },
  { to: '/agenda', label: 'Agenda' },
  { to: '/suscripciones', label: 'Suscripciones' },
  { to: '/portal', label: 'Portal alumno' },
  { to: '/pacientes', label: 'Pacientes' },
  { to: '/finanzas', label: 'Finanzas' },
];

export const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div>
          <p className="app-shell__eyebrow">Moviu Studio</p>
          <h1>Panel Profesional</h1>
        </div>
        <div className="app-shell__cta-group">
          <button className="primary">Crear servicio</button>
          <button className="ghost">Enviar aviso</button>
        </div>
      </header>
      <div className="app-shell__body">
        <nav className="app-shell__nav">
          {navLinks.map((link) => (
            <NavLink key={link.to} to={link.to} className={({ isActive }) => (isActive ? 'active' : '')} end={link.to === '/'}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <main className="app-shell__content">{children}</main>
      </div>
    </div>
  );
};
