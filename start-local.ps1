param(
    [ValidateSet('ollama', 'api', 'worker', 'frontend')]
    [string[]]$Services = @('ollama', 'api', 'worker', 'frontend')
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$RuntimeLogDir = Join-Path $RepoRoot 'logs/runtime'
New-Item -ItemType Directory -Path $RuntimeLogDir -Force | Out-Null
$env:RUNTIME_LOG_DIR = $RuntimeLogDir

foreach ($Service in $Services) {
    $Port = $null
    $WorkingDirectory = $RepoRoot
    switch ($Service) {
        'ollama' {
            $OllamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
            $Executable = if ($OllamaCommand) { $OllamaCommand.Source } else { Join-Path $RepoRoot 'backend/data/runtime/ollama/ollama.exe' }
            if (-not (Test-Path -LiteralPath $Executable)) { throw 'Install Ollama or provide backend/data/runtime/ollama/ollama.exe.' }
            $Arguments = @('serve')
            $env:OLLAMA_HOST = '127.0.0.1:11434'
            $env:OLLAMA_NO_CLOUD = '1'
            if (-not $env:OLLAMA_CONTEXT_LENGTH) { $env:OLLAMA_CONTEXT_LENGTH = '32768' }
            $Port = 11434
        }
        'api' {
            $Executable = (Get-Command python).Source
            $Arguments = @('-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '8000')
            $Port = 8000
        }
        'worker' {
            $Executable = (Get-Command python).Source
            $Arguments = @('-m', 'backend.worker')
        }
        'frontend' {
            $Executable = (Get-Command node).Source
            $WorkingDirectory = Join-Path $RepoRoot 'frontend'
            if (-not (Test-Path -LiteralPath (Join-Path $WorkingDirectory '.next/BUILD_ID'))) { throw 'Build frontend first: cd frontend; npm run build.' }
            $Arguments = @('node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', '3000')
            $Port = 3000
        }
    }
    if ($Port -and (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
        Write-Output "$Service already listens on port $Port."
        continue
    }
    $PidPath = Join-Path $RuntimeLogDir "$Service.pid"
    if ($Service -eq 'worker' -and (Test-Path -LiteralPath $PidPath)) {
        $ExistingId = [int](Get-Content -LiteralPath $PidPath)
        $ExistingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $ExistingId"
        if ($ExistingProcess -and $ExistingProcess.CommandLine -match '-m\s+backend\.worker(?:\s|$)') {
            Write-Output 'worker already runs.'
            continue
        }
    }
    $StartedProcess = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $RuntimeLogDir "$Service.stdout.log") `
        -RedirectStandardError (Join-Path $RuntimeLogDir "$Service.stderr.log") -PassThru
    Set-Content -LiteralPath $PidPath -Value $StartedProcess.Id
    Write-Output "$Service started, PID $($StartedProcess.Id); logs/runtime/$Service.*.log"
}
