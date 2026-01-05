#!/usr/bin/env python3
"""Utilidad de línea de comandos para descubrir servidores Moviu Print Server en la red local."""

from __future__ import annotations

import argparse
import json
import sys

try:
    from moviu_server.mdns import discover_moviu_servers
except ImportError:
    # If running as standalone, add parent to path
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from moviu_server.mdns import discover_moviu_servers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descubre servidores Moviu Print Server en la red local via mDNS/DNS-SD.",
        epilog="Ejemplo: python discover.py --timeout 5 --json",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=3.0,
        help="Tiempo de espera en segundos (default: 3.0)",
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Salida en formato JSON",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mostrar información detallada",
    )

    args = parser.parse_args()

    if not args.json:
        print(f"🔍 Buscando servidores Moviu en la red local ({args.timeout}s)...")
        print()

    servers = discover_moviu_servers(timeout=args.timeout)

    if args.json:
        print(json.dumps({"servers": servers, "count": len(servers)}, indent=2))
        return

    if not servers:
        print("❌ No se encontraron servidores Moviu en la red local.")
        print()
        print("Sugerencias:")
        print("  • Verifica que el servidor Moviu esté ejecutándose")
        print("  • Asegúrate de estar en la misma red local")
        print("  • Intenta aumentar el timeout: --timeout 5")
        sys.exit(1)

    print(f"✅ Se encontraron {len(servers)} servidor(es):\n")

    for i, server in enumerate(servers, 1):
        name = server.get("name", "Desconocido").replace("._moviu-print._tcp.local.", "")
        addresses = server.get("addresses", [])
        port = server.get("port", "?")
        props = server.get("properties", {})

        print(f"  [{i}] {name}")
        print(f"      📍 Direcciones: {', '.join(addresses) if addresses else 'N/A'}")
        print(f"      🔌 Puerto: {port}")
        print(f"      🔗 URL: https://{addresses[0] if addresses else 'localhost'}:{port}")

        if args.verbose and props:
            print(f"      📋 Propiedades:")
            for key, value in props.items():
                print(f"         • {key}: {value}")
        print()

    print("💡 Para usar un servidor, copia la URL y añade la API Key del servidor.")


if __name__ == "__main__":
    main()
