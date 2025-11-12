const members = [
  { name: 'Ana Torres', plan: 'Máximo 3×/sem', status: 'Activa', nextClass: 'Lunes 15:00' },
  { name: 'Pedro Díaz', plan: 'Básico 1×/sem', status: 'Activa', nextClass: 'Miércoles 18:00' }
];

export default function MembersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Miembros</h2>
        <p className="text-sm text-slate-400">
          Administra suscripciones, recuperos y acceso al portal del alumno.
        </p>
      </div>
      <div className="overflow-hidden rounded-lg border border-slate-800">
        <table className="min-w-full divide-y divide-slate-800 text-sm">
          <thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-4 py-3 text-left">Nombre</th>
              <th className="px-4 py-3 text-left">Plan</th>
              <th className="px-4 py-3 text-left">Estado</th>
              <th className="px-4 py-3 text-left">Próxima clase</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-950/50">
            {members.map((member) => (
              <tr key={member.name}>
                <td className="px-4 py-3 text-slate-100">{member.name}</td>
                <td className="px-4 py-3 text-slate-300">{member.plan}</td>
                <td className="px-4 py-3 text-emerald-400">{member.status}</td>
                <td className="px-4 py-3 text-slate-300">{member.nextClass}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
