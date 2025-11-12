export default function SignUpPage() {
  return (
    <div className="mx-auto mt-20 max-w-sm rounded-xl border border-slate-800 bg-slate-900/60 p-6 text-center">
      <h1 className="text-lg font-semibold text-slate-100">Crear cuenta de estudio</h1>
      <p className="mt-2 text-sm text-slate-400">Configura tu tenant y comienza a agendar.</p>
      <form className="mt-6 space-y-3">
        <input type="text" placeholder="Nombre del estudio" className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" />
        <input type="email" placeholder="Email" className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" />
        <button type="submit" className="w-full rounded-md bg-brand px-4 py-2 text-sm font-semibold text-brand-foreground">
          Crear tenant
        </button>
      </form>
    </div>
  );
}
