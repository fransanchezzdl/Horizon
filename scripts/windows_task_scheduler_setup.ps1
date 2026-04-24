# PowerShell Script para configurar automatización en Windows Task Scheduler
# 
# Uso:
#   .\windows_task_scheduler_setup.ps1 -Action Create
#   .\windows_task_scheduler_setup.ps1 -Action Delete
#   .\windows_task_scheduler_setup.ps1 -Action Status
#
# IMPORTANTE: Ejecutar como Administrador

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Create", "Delete", "Status", "RunNow")]
    [string]$Action,
    
    [string]$PythonPath = "python",
    [string]$ScriptPath = "D:\Uni\TFG\Horizon\scripts\scheduler_daemon.py",
    [string]$TaskName = "Horizon-Model-Training",
    [string]$TaskHour = "2",  # 2 AM
    [string]$WorkingDir = "D:\Uni\TFG\Horizon"
)

# Verificar si se ejecuta como Admin
$isAdmin = [bool]([System.Security.Principal.WindowsIdentity]::GetCurrent().Groups -match "S-1-5-32-544")
if (-not $isAdmin) {
    Write-Error "Este script requiere permisos de Administrador. Por favor, ejecutar como Admin."
    exit 1
}

Write-Host "================================" -ForegroundColor Cyan
Write-Host "HORIZON — Windows Task Scheduler" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

function Test-PythonEnvironment {
    """Verifica si Python y las dependencias están disponibles."""
    Write-Host "🔍 Verificando entorno Python..." -ForegroundColor Yellow
    
    try {
        $pythonVersion = & $PythonPath --version 2>&1
        Write-Host "✅ Python encontrado: $pythonVersion" -ForegroundColor Green
        
        # Verificar APScheduler
        & $PythonPath -c "import apscheduler" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ APScheduler instalado" -ForegroundColor Green
        } else {
            Write-Host "⚠️ APScheduler no encontrado. Instalando..." -ForegroundColor Yellow
            & $PythonPath -m pip install apscheduler --quiet
            Write-Host "✅ APScheduler instalado" -ForegroundColor Green
        }
        
        return $true
    } catch {
        Write-Host "❌ Error: Python no encontrado en $PythonPath" -ForegroundColor Red
        Write-Host "   Instala Python desde https://www.python.org/downloads/" -ForegroundColor Red
        return $false
    }
}

function Create-TrainingTask {
    """Crea la tarea de entrenamiento automático."""
    Write-Host "`n📝 Creando tarea de Windows Task Scheduler..." -ForegroundColor Yellow
    
    # Verificar si la tarea ya existe
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "⚠️ La tarea ya existe. Eliminando versión anterior..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    # Crear trigger (cada día a la hora especificada)
    $trigger = New-ScheduledTaskTrigger -Daily -At "$($TaskHour):00:00"
    
    # Crear acción (ejecutar Python)
    $action = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument "`"$ScriptPath`" --foreground" `
        -WorkingDirectory $WorkingDir
    
    # Configuración de la tarea
    $settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -AllowStartIfOnBatteries
    
    # Crear la tarea
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Trigger $trigger `
        -Action $action `
        -Settings $settings `
        -RunLevel Highest `
        -Force `
        -ErrorAction Stop | Out-Null
    
    Write-Host "✅ Tarea creada exitosamente" -ForegroundColor Green
    Write-Host "   Nombre: $TaskName" -ForegroundColor Green
    Write-Host "   Ejecución: Cada día a las $TaskHour:00" -ForegroundColor Green
    Write-Host "   Script: $ScriptPath" -ForegroundColor Green
    
    # Programar la primera ejecución para mañana a la hora indicada
    Get-ScheduledTask -TaskName $TaskName | Start-ScheduledTask -ErrorAction SilentlyContinue
    Write-Host "✅ Tarea programada para mañana a las $TaskHour:00 y cada día subsecuente" -ForegroundColor Green
}

function Delete-TrainingTask {
    """Elimina la tarea de entrenamiento."""
    Write-Host "`n🗑️ Eliminando tarea de Windows Task Scheduler..." -ForegroundColor Yellow
    
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "✅ Tarea eliminada exitosamente" -ForegroundColor Green
    } else {
        Write-Host "⚠️ La tarea no existe" -ForegroundColor Yellow
    }
}

function Show-TaskStatus {
    """Muestra el estado de la tarea."""
    Write-Host "`n📊 Estado de la tarea..." -ForegroundColor Yellow
    
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "❌ La tarea no está registrada" -ForegroundColor Red
        return
    }
    
    Write-Host "✅ Tarea encontrada" -ForegroundColor Green
    Write-Host "   Nombre: $($task.TaskName)" -ForegroundColor Green
    Write-Host "   Estado: $($task.State)" -ForegroundColor Green
    
    # Obtener información de la última ejecución
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
    if ($taskInfo.LastRunTime) {
        Write-Host "   Última ejecución: $($taskInfo.LastRunTime)" -ForegroundColor Green
        Write-Host "   Resultado: $($taskInfo.LastTaskResult)" -ForegroundColor Green
    }
    
    # Próxima ejecución prevista
    if ($task.Triggers) {
        $trigger = $task.Triggers[0]
        if ($trigger -is [Microsoft.Win32.TaskScheduler.DailyTrigger]) {
            $nextRun = [DateTime]::Now.Date.AddHours($TaskHour)
            if ($nextRun -le [DateTime]::Now) {
                $nextRun = $nextRun.AddDays(1)
            }
            Write-Host "   Próxima ejecución: $nextRun" -ForegroundColor Green
        }
    }
}

function Run-TaskNow {
    """Ejecuta la tarea inmediatamente."""
    Write-Host "`n▶️ Ejecutando tarea ahora..." -ForegroundColor Yellow
    
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "❌ La tarea no está registrada" -ForegroundColor Red
        return
    }
    
    try {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "✅ Tarea iniciada" -ForegroundColor Green
        Write-Host "   Verifica el log en: D:\Uni\TFG\Horizon\logs\scheduler.log" -ForegroundColor Green
    } catch {
        Write-Host "❌ Error al ejecutar tarea: $_" -ForegroundColor Red
    }
}

# Verificar environment
if (-not (Test-PythonEnvironment)) {
    exit 1
}

# Ejecutar acción solicitada
switch ($Action) {
    "Create" {
        Create-TrainingTask
    }
    "Delete" {
        Delete-TrainingTask
    }
    "Status" {
        Show-TaskStatus
    }
    "RunNow" {
        Run-TaskNow
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Completado" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
