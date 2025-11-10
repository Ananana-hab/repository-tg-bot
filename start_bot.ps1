# Безопасный запуск бота с проверками

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "BTC PUMP/DUMP BOT - SAFE STARTER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Шаг 1: Проверка запущенных процессов
Write-Host "`n[1/3] Checking for running Python processes..." -ForegroundColor Yellow
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "WARNING: Found running Python processes:" -ForegroundColor Red
    $pythonProcs | Format-Table Id, ProcessName, StartTime -AutoSize
    $answer = Read-Host "Stop all Python processes? (y/n)"
    if ($answer -eq "y") {
        Stop-Process -Name python -Force
        Write-Host "OK: All Python processes stopped" -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        Write-Host "ERROR: Cannot start bot with other Python processes running" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "OK: No Python processes running" -ForegroundColor Green
}

# Шаг 2: Очистка Telegram webhook
Write-Host "`n[2/3] Clearing Telegram webhook..." -ForegroundColor Yellow
python clear_telegram.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Webhook clear had issues, but continuing..." -ForegroundColor Yellow
}

# Шаг 3: Запуск бота
Write-Host "`n[3/3] Starting bot..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "BOT STARTING - Press Ctrl+C to stop" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Start-Sleep -Seconds 1

python main.py
