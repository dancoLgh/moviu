import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { ServicesPage } from './pages/ServicesPage';
import { AgendaPage } from './pages/AgendaPage';
import { SubscriptionsPage } from './pages/SubscriptionsPage';
import { PortalPage } from './pages/PortalPage';
import { PatientsPage } from './pages/PatientsPage';
import { FinancesPage } from './pages/FinancesPage';

export const App = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/servicios" element={<ServicesPage />} />
        <Route path="/agenda" element={<AgendaPage />} />
        <Route path="/suscripciones" element={<SubscriptionsPage />} />
        <Route path="/portal" element={<PortalPage />} />
        <Route path="/pacientes" element={<PatientsPage />} />
        <Route path="/finanzas" element={<FinancesPage />} />
      </Routes>
    </Layout>
  );
};
