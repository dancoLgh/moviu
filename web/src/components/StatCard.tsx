interface StatCardProps {
  label: string;
  value: string;
  trend?: string;
  status?: 'success' | 'warning' | 'danger';
}

export const StatCard = ({ label, value, trend, status }: StatCardProps) => {
  return (
    <div className="card">
      <p className="app-shell__eyebrow" style={{ marginBottom: 0 }}>
        {label}
      </p>
      <h3 style={{ fontSize: '1.8rem' }}>{value}</h3>
      {trend && <span className={`badge ${status ?? 'success'}`}>{trend}</span>}
    </div>
  );
};
