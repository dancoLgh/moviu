"""Responsive public page for installing the Moviu local CA certificate."""

from __future__ import annotations

from html import escape


def render_certificate_portal(
    server_url: str,
    download_url: str,
    fingerprint: str | None,
) -> str:
    """Render the certificate download and installation guide."""

    safe_server_url = escape(server_url)
    safe_download_url = escape(download_url, quote=True)
    safe_fingerprint = escape(fingerprint or "Certificado no disponible")
    download_action = (
        f'<a class="primary-button" href="{safe_download_url}" download>Descargar certificado CA</a>'
        if fingerprint
        else '<span class="primary-button disabled">Certificado no disponible</span>'
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#071521">
  <title>Instalar certificado | Moviu</title>
  <style>
    :root {{
      color-scheme: dark;
      --ink: #f4f8fb;
      --muted: #9db0bf;
      --line: rgba(157, 176, 191, .18);
      --surface: rgba(13, 37, 52, .86);
      --cyan: #2dd4bf;
      --navy: #071521;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        radial-gradient(circle at 88% 8%, rgba(45, 212, 191, .18), transparent 28rem),
        radial-gradient(circle at 4% 70%, rgba(59, 130, 246, .14), transparent 30rem),
        var(--navy);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .16;
      background-image: linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, black, transparent 72%);
    }}
    .shell {{ width: min(1080px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 56px; position: relative; }}
    nav {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 52px; }}
    .brand {{ display: flex; align-items: center; gap: 11px; font-size: 1.05rem; font-weight: 750; letter-spacing: -.02em; }}
    .brand-mark {{
      display: grid; place-items: center; width: 37px; height: 37px; border-radius: 12px;
      color: #05231f; background: linear-gradient(145deg, #5eead4, #22c55e); font-weight: 900;
      box-shadow: 0 10px 30px rgba(45, 212, 191, .25);
    }}
    .secure {{ color: #9ce8d9; border: 1px solid rgba(45,212,191,.3); background: rgba(45,212,191,.09); padding: 7px 11px; border-radius: 999px; font-size: .78rem; }}
    .hero {{ display: grid; grid-template-columns: 1.25fr .75fr; gap: 34px; align-items: center; margin-bottom: 42px; }}
    .eyebrow {{ color: #62e7d2; text-transform: uppercase; letter-spacing: .16em; font-weight: 800; font-size: .72rem; }}
    h1 {{ margin: 13px 0 18px; max-width: 760px; font-size: clamp(2.5rem, 7vw, 5.7rem); line-height: .94; letter-spacing: -.065em; }}
    .lead {{ max-width: 650px; color: var(--muted); font-size: clamp(1rem, 2vw, 1.16rem); line-height: 1.65; }}
    .primary-button {{
      display: inline-flex; justify-content: center; align-items: center; margin-top: 22px; min-height: 50px;
      padding: 0 20px; border-radius: 13px; color: #041b18; background: linear-gradient(135deg, #5eead4, #34d399);
      text-decoration: none; font-weight: 850; box-shadow: 0 14px 38px rgba(45,212,191,.23); transition: transform .18s ease;
    }}
    .primary-button:hover {{ transform: translateY(-2px); }}
    .primary-button.disabled {{ opacity: .45; pointer-events: none; }}
    .cert-card {{ padding: 24px; border: 1px solid var(--line); border-radius: 22px; background: linear-gradient(145deg, rgba(21,57,73,.86), rgba(8,29,43,.9)); box-shadow: 0 25px 70px rgba(0,0,0,.24); }}
    .cert-icon {{ width: 52px; height: 62px; border-radius: 9px; border: 2px solid #5eead4; position: relative; margin-bottom: 26px; }}
    .cert-icon::after {{ content: "CA"; position: absolute; right: -13px; bottom: -11px; display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: #5eead4; color: #06231f; font-weight: 900; font-size: .72rem; }}
    .meta-label {{ margin: 0 0 5px; color: var(--muted); font-size: .73rem; text-transform: uppercase; letter-spacing: .1em; }}
    .meta-value {{ margin: 0 0 18px; overflow-wrap: anywhere; font: 600 .88rem/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; }}
    .guide {{ padding: 28px; border: 1px solid var(--line); border-radius: 24px; background: var(--surface); backdrop-filter: blur(14px); }}
    .guide h2 {{ margin: 0 0 8px; font-size: clamp(1.5rem, 4vw, 2.15rem); letter-spacing: -.035em; }}
    .guide-intro {{ margin: 0 0 24px; color: var(--muted); }}
    .tab-input {{ position: absolute; width: 1px; height: 1px; opacity: 0; }}
    .tabs {{ display: flex; gap: 8px; padding: 5px; border-radius: 14px; background: rgba(2, 14, 23, .52); overflow-x: auto; }}
    .tabs label {{ flex: 1; min-width: 100px; padding: 10px 14px; border-radius: 10px; color: var(--muted); text-align: center; cursor: pointer; font-weight: 750; }}
    #windows:checked ~ .tabs label[for="windows"], #android:checked ~ .tabs label[for="android"], #linux:checked ~ .tabs label[for="linux"] {{ color: white; background: #173d56; box-shadow: inset 0 0 0 1px rgba(94,234,212,.2); }}
    #windows:focus-visible ~ .tabs label[for="windows"], #android:focus-visible ~ .tabs label[for="android"], #linux:focus-visible ~ .tabs label[for="linux"] {{ outline: 3px solid #5eead4; outline-offset: 2px; }}
    .panel {{ display: none; padding-top: 20px; }}
    #windows:checked ~ .panels .windows, #android:checked ~ .panels .android, #linux:checked ~ .panels .linux {{ display: block; }}
    ol {{ margin: 0; padding: 0; list-style: none; counter-reset: steps; display: grid; gap: 10px; }}
    li {{
      counter-increment: steps;
      display: grid;
      grid-template-columns: 38px minmax(0, 1fr);
      gap: 14px;
      align-items: start;
      padding: 15px 16px;
      color: #d9e5ec;
      background: rgba(5, 24, 36, .42);
      border: 1px solid rgba(157, 176, 191, .12);
      border-radius: 14px;
      line-height: 1.55;
    }}
    li::before {{
      content: counter(steps);
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 11px;
      color: #7cebd8;
      background: rgba(45,212,191,.1);
      border: 1px solid rgba(45,212,191,.24);
      font-weight: 850;
    }}
    .step-content {{ min-width: 0; padding-top: 4px; }}
    .step-content strong {{ color: #f5fbff; font-weight: 800; }}
    .follow-up {{ display: block; margin-top: 10px; }}
    code {{ color: #a7f3d0; background: #06131e; border: 1px solid var(--line); border-radius: 6px; padding: 2px 6px; }}
    code.command {{ display: block; max-width: 100%; margin-top: 9px; padding: 10px 12px; overflow-x: auto; white-space: nowrap; line-height: 1.45; }}
    .note {{ margin-top: 20px; padding: 14px 16px; border-left: 3px solid #fbbf24; border-radius: 8px; color: #d9e5ec; background: rgba(251,191,36,.08); line-height: 1.55; }}
    footer {{ margin-top: 25px; color: #7890a1; font-size: .78rem; text-align: center; }}
    @media (max-width: 760px) {{
      .shell {{ width: min(100% - 22px, 1080px); padding-top: 16px; }}
      nav {{ margin-bottom: 34px; }}
      .hero {{ grid-template-columns: 1fr; gap: 24px; }}
      h1 {{ font-size: clamp(2.6rem, 15vw, 4.4rem); }}
      .cert-card, .guide {{ padding: 20px; border-radius: 19px; }}
      .primary-button {{ width: 100%; }}
      .secure {{ display: none; }}
      li {{ grid-template-columns: 34px minmax(0, 1fr); gap: 11px; padding: 13px 12px; }}
      li::before {{ width: 32px; height: 32px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <nav>
      <div class="brand"><span class="brand-mark">M</span> Moviu Print Server</div>
      <span class="secure">Certificado público local</span>
    </nav>
    <section class="hero">
      <div>
        <div class="eyebrow">Configura HTTPS una sola vez</div>
        <h1>Conecta este dispositivo a Moviu.</h1>
        <p class="lead">Instala la autoridad certificadora local para que tu navegador y tus aplicaciones confíen en la conexión segura con este servidor de impresión.</p>
        {download_action}
      </div>
      <aside class="cert-card">
        <div class="cert-icon" aria-hidden="true"></div>
        <p class="meta-label">Servidor</p>
        <p class="meta-value">{safe_server_url}</p>
        <p class="meta-label">Huella SHA-256</p>
        <p class="meta-value">{safe_fingerprint}</p>
      </aside>
    </section>
    <section class="guide">
      <h2>Cómo instalarlo</h2>
      <p class="guide-intro">Selecciona tu sistema y sigue los pasos. Reinicia el navegador al terminar.</p>
      <input class="tab-input" type="radio" name="platform" id="windows" aria-controls="windows-panel" checked>
      <input class="tab-input" type="radio" name="platform" id="android" aria-controls="android-panel">
      <input class="tab-input" type="radio" name="platform" id="linux" aria-controls="linux-panel">
      <div class="tabs" role="group" aria-label="Sistema operativo">
        <label id="windows-label" for="windows">Windows</label>
        <label id="android-label" for="android">Android</label>
        <label id="linux-label" for="linux">Linux</label>
      </div>
      <div class="panels">
        <div class="panel windows" id="windows-panel" role="region" aria-labelledby="windows-label">
          <ol>
            <li><div class="step-content">Descarga <strong>moviu-ca.crt</strong> con el botón superior y abre el archivo.</div></li>
            <li><div class="step-content">Selecciona <strong>Instalar certificado</strong>. Puedes usar Usuario actual; Equipo local requerirá permisos de administrador.</div></li>
            <li><div class="step-content">Elige <strong>Colocar todos los certificados en el siguiente almacén</strong> y selecciona <strong>Entidades de certificación raíz de confianza</strong>.</div></li>
            <li><div class="step-content">Finaliza el asistente, acepta la advertencia de seguridad y reinicia el navegador.</div></li>
          </ol>
        </div>
        <div class="panel android" id="android-panel" role="region" aria-labelledby="android-label">
          <ol>
            <li><div class="step-content">Descarga <strong>moviu-ca.crt</strong>. Si Android pregunta el uso, selecciona <strong>Certificado CA</strong>.</div></li>
            <li><div class="step-content">Abre Ajustes y busca <strong>Instalar un certificado</strong>. Suele estar en Seguridad y privacidad, Más ajustes de seguridad.</div></li>
            <li><div class="step-content">Selecciona <strong>Certificado CA</strong>, confirma el aviso y abre el archivo descargado.</div></li>
            <li><div class="step-content">Asigna el nombre <strong>Moviu Local CA</strong> y reinicia Chrome o la aplicación que se conectará a Moviu.</div></li>
          </ol>
          <div class="note">Algunas aplicaciones administradas no aceptan certificados instalados por el usuario. En ese caso, su configuración de seguridad de red debe permitir esta CA.</div>
        </div>
        <div class="panel linux" id="linux-panel" role="region" aria-labelledby="linux-label">
          <ol>
            <li><div class="step-content">Descarga <strong>moviu-ca.crt</strong>.</div></li>
            <li><div class="step-content">En Debian o Ubuntu ejecuta:<code class="command">sudo cp ~/Downloads/moviu-ca.crt /usr/local/share/ca-certificates/</code></div></li>
            <li><div class="step-content">Actualiza el almacén:<code class="command">sudo update-ca-certificates</code><span class="follow-up">En Fedora copia el certificado en <code>/etc/pki/ca-trust/source/anchors/</code> y ejecuta:</span><code class="command">sudo update-ca-trust</code></div></li>
            <li><div class="step-content">Reinicia el navegador. En Firefox, si aún aparece el aviso, importa el archivo desde Privacidad y seguridad, Certificados, Autoridades.</div></li>
          </ol>
        </div>
      </div>
    </section>
    <footer>Comparte este certificado únicamente dentro de tu red de confianza. Moviu nunca publica la clave privada.</footer>
  </main>
</body>
</html>"""
