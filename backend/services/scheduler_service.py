"""
Servicio de scheduler para entrenamientos automáticos del modelo.

Proporciona automatización de reentranamientos periódicos usando APScheduler.

Uso en FastAPI (agregar a main.py):
    
    from backend.services.scheduler_service import scheduler_service
    
    @app.on_event("startup")
    async def startup_event():
        scheduler_service.start()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        scheduler_service.stop()

Características:
- Entrenamientos automáticos cada X horas
- Logging detallado de cada ejecución
- Manejo de errores robusto
- Notificaciones opcionales via email/slack
- Estadísticas de ejecuciones

Configuración en backend/config.py:
    TRAINING_INTERVAL_HOURS = 24  # Reentrenar cada 24 horas
    TRAINING_START_HOUR = 2       # A las 2 AM
    TRAINING_ENABLED = True       # Habilitar/deshabilitar
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logging.warning("APScheduler no instalado. Instala: pip install apscheduler")


logger = logging.getLogger(__name__)


class TrainingScheduler:
    """Gestor de entrenamientos automáticos con APScheduler."""
    
    def __init__(self, interval_hours: int = 24, start_hour: int = 2, enabled: bool = True):
        """
        Inicializa el scheduler.
        
        Args:
            interval_hours: Intervalo entre entrenamientos en horas (ej: 24)
            start_hour: Hora del día para ejecutar (0-23, default 2 = 2 AM)
            enabled: Si False, no inicia entrenamientos automáticos
        """
        self.interval_hours = interval_hours
        self.start_hour = start_hour
        self.enabled = enabled and APSCHEDULER_AVAILABLE
        self.scheduler = None
        self.execution_history: List[Dict] = []
        self.next_run: Optional[datetime] = None
        
        if not APSCHEDULER_AVAILABLE:
            logger.warning("⚠️ Scheduler deshabilitado (APScheduler no disponible)")
        elif not enabled:
            logger.info("ℹ️ Scheduler deshabilitado en configuración")
    
    def start(self) -> bool:
        """
        Inicia el scheduler de entrenamientos.
        
        Returns:
            bool: True si se inició exitosamente
        """
        if not self.enabled:
            logger.info("Scheduler no habilitado, omitiendo inicio")
            return False
        
        try:
            self.scheduler = BackgroundScheduler()
            
            # Configurar trigger cada X horas a una hora específica
            trigger = CronTrigger(
                hour=self.start_hour,
                minute=0,
                second=0,
                timezone='Europe/Madrid'  # Ajusta según tu zona horaria
            )
            
            self.scheduler.add_job(
                func=self._training_job,
                trigger=trigger,
                id='horizon_training',
                name='Horizon Ensemble Training',
                misfire_grace_time=600,  # 10 minutos de tolerancia
                coalesce=True,  # Ejecutar una sola vez si se puede
                replace_existing=True
            )
            
            self.scheduler.start()
            
            # Calcular próxima ejecución
            self._update_next_run()
            
            logger.info("=" * 70)
            logger.info("✅ SCHEDULER INICIADO")
            logger.info(f"   Próxima ejecución: {self.next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"   Hora diaria: {self.start_hour:02d}:00 (servidor)")
            logger.info("=" * 70)
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error iniciando scheduler: {e}", exc_info=True)
            return False
    
    def stop(self) -> None:
        """Detiene el scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✅ Scheduler detenido")
    
    def _update_next_run(self) -> None:
        """Calcula la próxima ejecución programada."""
        now = datetime.now()
        next_run = now.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        self.next_run = next_run
    
    def _training_job(self) -> None:
        """
        Función que ejecuta el entrenamiento masivo.
        
        Se despliega en un thread del scheduler, permitiendo que el servidor
        siga respondiendo mientras se entrena.
        """
        from ..models.train_all import main as train_all_main
        
        execution_start = datetime.now()
        
        logger.info("=" * 70)
        logger.info(f"🚀 INICIANDO ENTRENAMIENTO AUTOMÁTICO")
        logger.info(f"   Timestamp: {execution_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        try:
            # Ejecutar el entrenamiento masivo
            train_all_main(verify_db=True)  # Con verificación
            
            execution_end = datetime.now()
            elapsed = (execution_end - execution_start).total_seconds()
            
            # Registrar ejecución exitosa
            status = "SUCCESS"
            log_level = logger.info
            
            log_level(f"✅ ENTRENAMIENTO COMPLETADO")
            log_level(f"   Duración: {elapsed:.1f}s")
            log_level(f"   Timestamp final: {execution_end.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            execution_end = datetime.now()
            elapsed = (execution_end - execution_start).total_seconds()
            status = "FAILED"
            
            logger.error(f"❌ ERROR EN ENTRENAMIENTO AUTOMÁTICO: {e}")
            logger.error(f"   Duración antes del error: {elapsed:.1f}s", exc_info=True)
        
        # Registrar en histórico
        self.execution_history.append({
            "timestamp": execution_start,
            "status": status,
            "duration_seconds": elapsed,
            "error": str(e) if status == "FAILED" else None
        })
        
        # Limpiar histórico (mantener últimos 100)
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
        
        # Actualizar próxima ejecución
        self._update_next_run()
        logger.info(f"⏳ Próxima ejecución: {self.next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def get_status(self) -> Dict:
        """
        Obtiene el estado actual del scheduler.
        
        Returns:
            Dict con información de estado
        """
        return {
            "enabled": self.enabled,
            "running": self.scheduler and self.scheduler.running,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "interval_hours": self.interval_hours,
            "start_hour": self.start_hour,
            "last_execution": None if not self.execution_history else {
                "timestamp": self.execution_history[-1]["timestamp"].isoformat(),
                "status": self.execution_history[-1]["status"],
                "duration_seconds": self.execution_history[-1]["duration_seconds"],
            },
            "total_executions": len(self.execution_history),
            "successful_executions": sum(1 for e in self.execution_history if e["status"] == "SUCCESS"),
            "failed_executions": sum(1 for e in self.execution_history if e["status"] == "FAILED"),
        }
    
    def get_execution_history(self, limit: int = 20) -> List[Dict]:
        """
        Obtiene el histórico de ejecuciones.
        
        Args:
            limit: Máximo número de registros a retornar
        
        Returns:
            Lista de ejecuciones más recientes
        """
        return self.execution_history[-limit:]


# Instancia global del scheduler
# Configurar desde backend/config.py si es necesario
scheduler_service = TrainingScheduler(
    interval_hours=24,
    start_hour=2,  # 2 AM
    enabled=True  # Cambiar a False para deshabilitar
)
