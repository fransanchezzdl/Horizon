"""
Script CLI para el registro diario de predicciones y resolución de outcomes.

Uso desde la raíz del proyecto:

  # Registrar predicciones de hoy para todos los tickers
  python -m backend.scripts.daily_log log

  # Registrar solo tickers concretos
  python -m backend.scripts.daily_log log --tickers KO AAPL TSLA

  # Resolver predicciones cuyo horizonte ya ha pasado
  python -m backend.scripts.daily_log resolve

  # Ver estadísticas de fiabilidad de un ticker
  python -m backend.scripts.daily_log stats --ticker KO

  # Ver estadísticas de todos los tickers
  python -m backend.scripts.daily_log stats --all

  # Ejecutar log + resolve en un solo paso (uso típico diario)
  python -m backend.scripts.daily_log run

Recomendación: ejecutar `run` cada día laborable después del cierre del mercado
(ej. 22:00 hora España), antes de revisar la aplicación.
"""

import argparse
import json
import sys
import io
from datetime import date

# Windows usa cp1252 por defecto; forzar UTF-8 para que los emojis del modelo
# no rompan la ejecución al escribir en consola.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def cmd_log(args):
    from backend.services.prediction_log_service import log_daily_predictions

    tickers = args.tickers if args.tickers else None
    print(f"\n{'='*60}")
    print(f"  REGISTRO DE PREDICCIONES — {date.today()}")
    print(f"{'='*60}")

    result = log_daily_predictions(tickers)

    print(f"\n  Nuevas predicciones guardadas : {len(result['logged'])}")
    if result["logged"]:
        print(f"    {result['logged']}")

    print(f"  Omitidas (ya existían hoy)    : {len(result['skipped'])}")
    if result["skipped"]:
        print(f"    {result['skipped']}")

    if result["errors"]:
        print(f"\n  ERRORES ({len(result['errors'])}):")
        for err in result["errors"]:
            print(f"    [{err['ticker']}] {err['error']}")

    print()


def cmd_resolve(args):
    from backend.services.prediction_log_service import resolve_pending_predictions

    print(f"\n{'='*60}")
    print(f"  RESOLUCIÓN DE PREDICCIONES PENDIENTES — {date.today()}")
    print(f"{'='*60}\n")

    result = resolve_pending_predictions()

    if not result["resolved"] and not result["failed"]:
        print("  No hay predicciones pendientes de resolver.")
    else:
        print(f"  {'Ticker':<10} {'Predicha':<12} {'Real':<12} {'Resultado'}")
        print(f"  {'─'*50}")
        for r in result["resolved"]:
            icono = "✓" if r["correcta"] else "✗"
            print(
                f"  {r['ticker']:<10} {r['predicha']:<12} {r['real']:<12} "
                f"{icono}  (retorno real: {r['retorno_real']:+.2f}%)"
            )

        if result["failed"]:
            print(f"\n  Sin resolver ({len(result['failed'])}):")
            for f in result["failed"]:
                print(f"    [{f['ticker']}] {f['reason']}")

    total_ok = len(result["resolved"])
    correctas = sum(1 for r in result["resolved"] if r["correcta"])
    if total_ok:
        print(f"\n  Aciertos esta sesión: {correctas}/{total_ok} ({correctas/total_ok*100:.0f}%)")
    print()


def cmd_stats(args):
    from backend.services.prediction_log_service import get_reliability_stats
    from backend.models.config import TICKERS

    tickers_list = []
    if args.all:
        tickers_list = TICKERS["stable"] + TICKERS["volatile"]
    elif args.ticker:
        tickers_list = [args.ticker.upper()]
    else:
        print("Especifica --ticker AAPL o --all")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"  ESTADÍSTICAS DE FIABILIDAD — {date.today()}")
    print(f"{'='*70}")
    print(f"  {'Ticker':<10} {'WF BA%':<10} {'WF±':<8} {'Live total':<12} {'Live acc%':<12} {'Señal'}")
    print(f"  {'─'*65}")

    for ticker in tickers_list:
        s = get_reliability_stats(ticker)
        wf     = s["walk_forward"]
        live   = s["live"]
        señal  = s["señal"]

        wf_ba  = f"{wf['ba_mean']:.1f}%" if wf else "N/A"
        wf_std = f"±{wf['ba_std']:.1f}" if wf else ""
        live_t = str(live["total"])
        live_a = f"{live['accuracy']:.1f}%" if live["accuracy"] is not None else f"({live['resueltas']} res.)"

        print(f"  {ticker:<10} {wf_ba:<10} {wf_std:<8} {live_t:<12} {live_a:<12} {señal}")

    print(f"\n  Baseline azar: 33.3%  |  WF = Walk-Forward offline  |  Live = predicciones en producción")
    print()


def cmd_run(args):
    """log + resolve en un paso."""
    cmd_log(args)
    cmd_resolve(args)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Gestión del registro de predicciones de Horizon"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # log
    p_log = sub.add_parser("log", help="Registrar predicciones de hoy")
    p_log.add_argument("--tickers", nargs="+", help="Tickers concretos (default: todos)")

    # resolve
    sub.add_parser("resolve", help="Resolver predicciones cuyo horizonte ya pasó")

    # stats
    p_stats = sub.add_parser("stats", help="Ver estadísticas de fiabilidad")
    g = p_stats.add_mutually_exclusive_group(required=True)
    g.add_argument("--ticker", help="Un ticker concreto")
    g.add_argument("--all",    action="store_true", help="Todos los tickers")

    # run (log + resolve)
    p_run = sub.add_parser("run", help="Log + resolve (uso diario recomendado)")
    p_run.add_argument("--tickers", nargs="+", help="Tickers concretos (default: todos)")

    args = parser.parse_args()

    dispatch = {
        "log":     cmd_log,
        "resolve": cmd_resolve,
        "stats":   cmd_stats,
        "run":     cmd_run,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
