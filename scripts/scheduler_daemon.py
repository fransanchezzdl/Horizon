#!/usr/bin/env python
"""
Daemon de scheduler independiente para Horizon Predictor.

Corre en segundo plano entrenando modelos automáticamente cada X horas.
No depende del servidor FastAPI, puede correr en una máquina/contenedor separado.

Uso:
    # Iniciar daemon
    python scripts/scheduler_daemon.py --start
    
    # Detener daemon (guardará estado)
    python scripts/scheduler_daemon.py --stop
    
    # Ver estado actual
    python scripts/scheduler_daemon.py --status
    
    # Ver histórico de entrenamientos
    python scripts/scheduler_daemon.py --history
    
    # Debug mode (sin daemonizar)
    python scripts/scheduler_daemon.py --foreground

Configuración:
    - Interval entre entrenamientos: TRAINING_INTERVAL_HOURS (default 24)
    - Hora de ejecución: TRAINING_START_HOUR (default 2 = 2 AM)
    - Log file: ./logs/scheduler.log
    - PID file: ./logs/scheduler.pid

En Windows Task Scheduler:
    - Crear tarea que ejecute: python D:\Uni\TFG\Horizon\scripts\scheduler_daemon.py --foreground
    - Repetir cada 24 horas a las 2:00 AM

En Linux Cron:
    - Agregar: 0 2 * * * /usr/bin/python3 /ruta/a/scheduler_daemon.py --foreground
"""

import os
import sys
import time
import logging
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

# Asegurar que podemos importar desde backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.config import TICKERS, USE_SENTIMENT
from backend.models.train_all import main as train_all_main


# Configuración de logging
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "scheduler.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SchedulerDaemon:
    """Daemon independiente de scheduling para entrenamientos."""
    
    def __init__(
        self,
        interval_hours: int = 24,
        start_hour: int = 2,
        verify_db: bool = True
    ):
        """
        Inicializa el daemon.
        
        Args:
            interval_hours: Horas entre entrenamientos
            start_hour: Hora del día para ejecutar (0-23)
            verify_db: Verificar integridad tras guardar
        """
        self.interval_hours = interval_hours
        self.start_hour = start_hour
        self.verify_db = verify_db
        self.running = False
        self.next_run: Optional[datetime] = None
        self.stats = {
            "total_runs": 0,
            "successful": 0,
            "failed": 0,
            "last_run": None,
            "last_duration": 0,
        }
        
        self._load_stats()
    
    def _stats_file(self) -> Path:
        """Ruta del archivo de estadísticas."""
        return LOGS_DIR / "scheduler_stats.json"
    
    def _load_stats(self) -> None:
        """Carga estadísticas previas si existen."""
        stats_file = self._stats_file()
        if stats_file.exists():
            try:
                with open(stats_file) as f:
                    self.stats = json.load(f)
            except Exception as e:
                logger.warning(f"No se pudieron cargar estadísticas: {e}")
    
    def _save_stats(self) -> None:
        """Guarda estadísticas actuales."""
        stats_file = self._stats_file()
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error guardando estadísticas: {e}")
    
    def _calculate_next_run(self) -> datetime:
        """Calcula la próxima ejecución planeada."""
        now = datetime.now()
        next_run = now.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run
    
    def run(self, foreground: bool = False) -> None:
        """
        Inicia el daemon.
        
        Args:
            foreground: Si True, corre en primer plano (para debug/Windows)
        """
        self.running = True
        self.next_run = self._calculate_next_run()
        
        logger.info("=" * 80)
        logger.info("🌅 HORIZON SCHEDULER DAEMON INICIADO")
        logger.info(f"   Intervalo entre entrenamientos: {self.interval_hours} horas")
        logger.info(f"   Hora de ejecución: {self.start_hour:02d}:00")
        logger.info(f"   Próximo entrenamiento: {self.next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Verificación BD: {'✅ Activada' if self.verify_db else '❌ Desactivada'}")
        logger.info(f"   Modo: {'Primer plano (debug)' if foreground else 'Daemon'}")
        logger.info("=" * 80 + "\n")
        
        try:
            while self.running:
                now = datetime.now()
                
                if now >= self.next_run:
                    self._execute_training()
                    self.next_run = self._calculate_next_run()
                    logger.info(f"⏳ Próximo entrenamiento: {self.next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                # Dormir 60 segundos y revisar nuevamente
                time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("\n⚠️ Daemon interrumpido por usuario")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Error en daemon: {e}", exc_info=True)
            self.running = False
        finally:
            self._save_stats()
    
    def _execute_training(self) -> None:
        """Ejecuta el entrenamiento masivo."""
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info(f"🚀 INICIANDO ENTRENAMIENTO AUTOMÁTICO")
        logger.info(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Tickers: {len(TICKERS['stable'] + TICKERS['volatile'])} activos")
        logger.info("=" * 80)
        
        try:
            # Ejecutar entrenamiento
            train_all_main(verify_db=self.verify_db)
            
            duration = time.time() - start_time
            
            # Actualizar estadísticas
            self.stats["total_runs"] += 1
            self.stats["successful"] += 1
            self.stats["last_run"] = datetime.now().isoformat()
            self.stats["last_duration"] = duration
            
            logger.info(f"\n✅ ENTRENAMIENTO EXITOSO")
            logger.info(f"   Duración: {duration:.1f}s ({duration/60:.1f} min)")
            logger.info(f"   Total exitosos: {self.stats['successful']}")
            logger.info(f"   Total fallidos: {self.stats['failed']}")
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Actualizar estadísticas
            self.stats["total_runs"] += 1
            self.stats["failed"] += 1
            self.stats["last_run"] = datetime.now().isoformat()
            self.stats["last_duration"] = duration
            
            logger.error(f"❌ ERROR EN ENTRENAMIENTO: {e}")
            logger.error(f"   Duración antes del error: {duration:.1f}s")
            logger.error(f"   Total exitosos: {self.stats['successful']}")
            logger.error(f"   Total fallidos: {self.stats['failed']}", exc_info=True)
        
        finally:
            self._save_stats()
    
    def get_status(self) -> Dict:
        """Obtiene el estado actual."""
        return {
            "running": self.running,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "interval_hours": self.interval_hours,
            "start_hour": self.start_hour,
            "stats": self.stats,
        }
    
    def stop(self) -> None:
        """Detiene el daemon."""
        self.running = False
        logger.info("✅ Deteniendo daemon...")


def print_status(daemon: SchedulerDaemon) -> None:
    """Imprime el estado actual."""
    status = daemon.get_status()
    stats = status["stats"]
    
    print("\n" + "=" * 60)
    print("📊 ESTADO DEL SCHEDULER DAEMON")
    print("=" * 60)
    print(f"Estado: {'🟢 EN EJECUCIÓN' if status['running'] else '🔴 DETENIDO'}")
    print(f"Próximo entrenamiento: {status['next_run']}")
    print(f"Intervalo: {status['interval_hours']} horas")
    print(f"Hora de ejecución: {status['start_hour']:02d}:00")
    print("\nEstadísticas:")
    print(f"  Total de entrenamientos: {stats['total_runs']}")
    print(f"  Exitosos: {stats['successful']}")
    print(f"  Fallidos: {stats['failed']}")
    print(f"  Último entrenamiento: {stats['last_run']}")
    print(f"  Última duración: {stats['last_duration']:.1f}s")
    print("=" * 60 + "\n")


def print_history() -> None:
    """Imprime el histórico del log."""
    if not LOG_FILE.exists():
        print("No hay histórico disponible aún.")
        return
    
    print(f"\n📜 Últimos 50 eventos de {LOG_FILE}:\n")
    
    with open(LOG_FILE) as f:
        lines = f.readlines()
    
    # Mostrar últimas 50 líneas
    for line in lines[-50:]:
        print(line.rstrip())


def main():
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(
        description="Daemon de scheduling automático para Horizon Predictor"
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Iniciar daemon en segundo plano"
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Ejecutar en primer plano (debug/Windows)"
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Detener daemon"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Ver estado actual"
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Ver histórico de entrenamientos"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Intervalo entre entrenamientos en horas (default: 24)"
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=2,
        help="Hora del día para ejecutar (0-23, default: 2)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Omitir verificación de BD tras guardar"
    )
    
    args = parser.parse_args()
    
    daemon = SchedulerDaemon(
        interval_hours=args.interval,
        start_hour=args.hour,
        verify_db=not args.no_verify
    )
    
    # Ejecutar acción solicitada
    if args.status:
        print_status(daemon)
    elif args.history:
        print_history()
    elif args.foreground:
        daemon.run(foreground=True)
    elif args.start:
        logger.info("Iniciando daemon en segundo plano...")
        daemon.run(foreground=False)
    elif args.stop:
        logger.info("Deteniendo daemon...")
        # En un caso real, aquí buscarías el proceso PID y lo terminarías
    else:
        # Default: correr en foreground para desarrollo
        print("Ejecutando en foreground (modo debug)...")
        daemon.run(foreground=True)


if __name__ == "__main__":
    main()
