export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Configuración del estudio</h2>
        <p className="text-sm text-slate-400">
          Ajusta datos del tenant, zona horaria, notificaciones y políticas de cancelación.
        </p>
      </div>
      <form className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/50 p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 text-sm">
            Nombre del estudio
            <input
              defaultValue="Elementos Pilates & Kine"
              className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-2 text-sm">
            Email de facturación
            <input defaultValue="billing@elementos.test" className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2" />
          </label>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 text-sm">
            Zona horaria
            <select className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2">
              <option value="America/Asuncion">America/Asuncion</option>
            </select>
          </label>
          <label className="flex flex-col gap-2 text-sm">
            Idioma
            <select className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2">
              <option value="es-PY">Español (PY)</option>
              <option value="en-US">English</option>
            </select>
          </label>
        </div>
        <button type="submit" className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-foreground">
          Guardar cambios
        </button>
      </form>
    </div>
  );
}
