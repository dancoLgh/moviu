# Moviu GitHub Pages and README Design

## Objective

Present Moviu Print Server to end users and developers with a clear installation path, an accurate technical overview, and a transparent account of why the project exists. The website and README should make the product feel approachable without hiding certificate, platform, or integration requirements.

## Message

Moviu was born from a practical need: printing from a web application should not require a heavy setup or repeated manual certificate work. It offers a focused alternative for projects that do not need the broader ecosystems of tools such as QZ Tray or JSPrintManager. The project was built 100% through vibe coding, combining a real operational need, AI-assisted iteration, and practical validation.

The vibe-coding origin appears as a badge in the hero and as a dedicated story section. It supports the product story but does not replace concrete evidence about features, security, and supported print modes.

## Website

The static site lives in `site/` and is deployed by GitHub Actions. It has no build-time framework or runtime dependency. Its visual system follows the desktop application: near-black navy backgrounds, slate-blue surfaces, electric-blue actions, cyan accents, restrained green status indicators, and a Segoe UI-compatible font stack.

The page includes a responsive header, product hero, CSS representation of the desktop dashboard, problem statement, three-step setup flow, supported formats, vibe-coding story, API example, security explanation, platform downloads, and documentation links. Reduced-motion preferences and keyboard navigation are respected.

## Documentation

The README becomes a concise project portal. Detailed setup and packaging instructions move to `docs/INSTALLATION.md`; discovery examples move to `docs/DISCOVERY.md`; API details remain in `docs/API_INTEGRACION.md`. Cross-links make each document reachable from both the README and website.

## Delivery

GitHub Pages deploys from `site/` on pushes to `main`. Pushing a `v*` tag runs tests, builds native Windows and Linux executables, creates the GitHub release with generated notes, and attaches both binaries. A manual dispatch remains available to rebuild an existing tag. Static-site tests validate navigation targets, local assets, download URLs, and core product messaging.
