#!/bin/bash

# Script para configurar automatización en Linux/Mac usando Cron
#
# Uso:
#   bash scripts/linux_cron_setup.sh --create
#   bash scripts/linux_cron_setup.sh --remove
#   bash scripts/linux_cron_setup.sh --status
#   bash scripts/linux_cron_setup.sh --test
#
# Requiere:
#   - Python 3.8+
#   - APScheduler: pip install apscheduler
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DAEMON_SCRIPT="$SCRIPT_DIR/scheduler_daemon.py"
CRON_JOB="0 2 * * * cd $PROJECT_DIR && $PYTHON_BIN $DAEMON_SCRIPT --foreground >> /tmp/horizon_training.log 2>&1"
CRON_COMMENT="# HORIZON MODEL TRAINING - Auto-retraining at 2 AM daily"
TEMP_CRON="/tmp/horizon_cron_$$.tmp"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}HORIZON — Linux Cron Setup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Funciones

check_python() {
    echo -e "${YELLOW}🔍 Verificando Python...${NC}"
    
    if ! command -v $PYTHON_BIN &> /dev/null; then
        echo -e "${RED}❌ Python no encontrado en $PYTHON_BIN${NC}"
        echo -e "${RED}   Instala Python 3.8+ desde https://www.python.org${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_BIN --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION encontrado${NC}"
    
    # Verificar APScheduler
    echo -e "${YELLOW}🔍 Verificando APScheduler...${NC}"
    if ! $PYTHON_BIN -c "import apscheduler" 2>/dev/null; then
        echo -e "${YELLOW}⚠️ APScheduler no instalado. Instalando...${NC}"
        $PYTHON_BIN -m pip install apscheduler --quiet
        echo -e "${GREEN}✅ APScheduler instalado${NC}"
    else
        echo -e "${GREEN}✅ APScheduler disponible${NC}"
    fi
}

create_cron_job() {
    echo -e "\n${YELLOW}📝 Creando entrada en cron...${NC}"
    
    # Obtener cron actual
    crontab -l > "$TEMP_CRON" 2>/dev/null || true
    
    # Verificar si ya existe
    if grep -q "scheduler_daemon.py" "$TEMP_CRON"; then
        echo -e "${YELLOW}⚠️ La tarea ya existe en cron. Actualizando...${NC}"
        grep -v "scheduler_daemon.py" "$TEMP_CRON" > "$TEMP_CRON.new"
        mv "$TEMP_CRON.new" "$TEMP_CRON"
    fi
    
    # Agregar comentario y trabajo
    echo "$CRON_COMMENT" >> "$TEMP_CRON"
    echo "$CRON_JOB" >> "$TEMP_CRON"
    
    # Instalar nuevo cron
    crontab "$TEMP_CRON"
    rm -f "$TEMP_CRON"
    
    echo -e "${GREEN}✅ Tarea de cron creada exitosamente${NC}"
    echo -e "${GREEN}   Ejecución: Cada día a las 2:00 AM${NC}"
    echo -e "${GREEN}   Script: $DAEMON_SCRIPT${NC}"
    echo -e "${GREEN}   Log: /tmp/horizon_training.log${NC}"
}

remove_cron_job() {
    echo -e "\n${YELLOW}🗑️ Eliminando entrada de cron...${NC}"
    
    # Obtener cron actual
    if crontab -l > "$TEMP_CRON" 2>/dev/null; then
        # Remover líneas relacionadas con scheduler_daemon
        grep -v "scheduler_daemon.py" "$TEMP_CRON" > "$TEMP_CRON.new"
        
        if ! diff -q "$TEMP_CRON" "$TEMP_CRON.new" > /dev/null 2>&1; then
            # Hay diferencias, instalar el nuevo cron
            if [ -s "$TEMP_CRON.new" ]; then
                crontab "$TEMP_CRON.new"
                echo -e "${GREEN}✅ Tarea removida${NC}"
            else
                # Si el archivo está vacío, limpiar cron
                crontab -r 2>/dev/null || true
                echo -e "${GREEN}✅ Tarea removida (todas las tareas de cron eliminadas)${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️ La tarea no existe en cron${NC}"
        fi
        
        rm -f "$TEMP_CRON" "$TEMP_CRON.new"
    else
        echo -e "${YELLOW}⚠️ No hay tareas en cron configuradas${NC}"
    fi
}

show_status() {
    echo -e "\n${YELLOW}📊 Estado de la automatización...${NC}"
    
    if crontab -l 2>/dev/null | grep -q "scheduler_daemon.py"; then
        echo -e "${GREEN}✅ Tarea de cron activa${NC}"
        
        echo -e "\n${BLUE}Configuración actual:${NC}"
        crontab -l | grep -A1 "HORIZON"
        
        if [ -f /tmp/horizon_training.log ]; then
            echo -e "\n${BLUE}Últimas 10 líneas del log:${NC}"
            tail -10 /tmp/horizon_training.log
        fi
    else
        echo -e "${RED}❌ Tarea de cron no configurada${NC}"
    fi
}

test_training() {
    echo -e "\n${YELLOW}▶️ Ejecutando entrenamiento de prueba...${NC}"
    echo -e "${YELLOW}   (Esto puede tomar varios minutos)${NC}\n"
    
    cd "$PROJECT_DIR"
    $PYTHON_BIN "$DAEMON_SCRIPT" --foreground || true
    
    echo -e "\n${GREEN}✅ Prueba completada${NC}"
}

show_help() {
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  --create      Crear entrada en cron para entrenamientos diarios"
    echo "  --remove      Remover entrada de cron"
    echo "  --status      Ver estado de la automatización"
    echo "  --test        Ejecutar prueba de entrenamiento"
    echo "  --help        Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  bash scripts/linux_cron_setup.sh --create"
    echo "  bash scripts/linux_cron_setup.sh --status"
    echo "  bash scripts/linux_cron_setup.sh --remove"
    echo ""
}

# Main
check_python

case "${1:-help}" in
    --create)
        create_cron_job
        ;;
    --remove)
        remove_cron_job
        ;;
    --status)
        show_status
        ;;
    --test)
        test_training
        ;;
    --help)
        show_help
        ;;
    *)
        echo -e "${RED}Opción desconocida: $1${NC}"
        show_help
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}✅ Completado${NC}"
echo -e "${BLUE}================================${NC}"
