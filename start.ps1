param(
    [int[]]$Ports = @(8000, 8001, 8002, 8003, 8004, 8501),
    [switch]$NoWait
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot "reports\logs"
New-Item -ItemType Directory -Force $LogDir | Out-Null

if (-not (Test-Path ".env")) {
    Write-Host "Arquivo .env não encontrado. Copiando .env.example para .env..."
    Copy-Item ".env.example" ".env"
}

Write-Host "==> Encerrando processos anteriores nas portas $($Ports -join ', ')..."
foreach ($port in $Ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

function Start-DemoProcess {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [string]$LogName
    )

    $stdout = Join-Path $LogDir "$LogName.out.log"
    $stderr = Join-Path $LogDir "$LogName.err.log"

    Write-Host "==> Iniciando $Name..."
    $process = Start-Process `
        -FilePath "python" `
        -ArgumentList $Arguments `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru

    return @{
        Name = $Name
        Process = $process
        Stdout = $stdout
        Stderr = $stderr
    }
}

function Test-Port {
    param([int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $result.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($result)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Wait-Port {
    param(
        [int]$Port,
        [string]$Name,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port -Port $Port) {
            Write-Host "OK  $Name em http://localhost:$Port"
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    Write-Host "ERRO $Name não abriu a porta $Port."
    return $false
}

$started = @()
$started += Start-DemoProcess "Agente Resumidor (porta 8001)" @("-m", "uvicorn", "agents.summarizer_agent:app", "--port", "8001", "--log-level", "warning") "summarizer"
$started += Start-DemoProcess "Agente de Sentimento (porta 8002)" @("-m", "uvicorn", "agents.sentiment_agent:app", "--port", "8002", "--log-level", "warning") "sentiment"
$started += Start-DemoProcess "Agente Categorizador (porta 8003)" @("-m", "uvicorn", "agents.categorizer_agent:app", "--port", "8003", "--log-level", "warning") "categorizer"
$started += Start-DemoProcess "Orquestrador (porta 8000)" @("-m", "uvicorn", "orchestrator.main:app", "--port", "8000", "--log-level", "warning") "orchestrator"

$oldMcpTransport = $env:MCP_TRANSPORT
$oldMcpPort = $env:MCP_PORT
$env:MCP_TRANSPORT = "streamable-http"
$env:MCP_PORT = "8004"
$started += Start-DemoProcess "Servidor MCP (porta 8004 /mcp)" @("mcp_server.py") "mcp"
$env:MCP_TRANSPORT = $oldMcpTransport
$env:MCP_PORT = $oldMcpPort

$started += Start-DemoProcess "Interface Streamlit (porta 8501)" @("-m", "streamlit", "run", "app.py", "--server.headless", "true") "streamlit"

Write-Host ""
Write-Host "==> Aguardando serviços..."
$checks = @(
    (Wait-Port 8001 "Agente Resumidor"),
    (Wait-Port 8002 "Agente de Sentimento"),
    (Wait-Port 8003 "Agente Categorizador"),
    (Wait-Port 8000 "Orquestrador"),
    (Wait-Port 8004 "MCP"),
    (Wait-Port 8501 "Streamlit")
)

if ($checks -contains $false) {
    Write-Host ""
    Write-Host "Algum serviço não iniciou. Veja os logs em: $LogDir"
    foreach ($item in $started) {
        Write-Host "- $($item.Name): $($item.Stderr)"
    }
    exit 1
}

Write-Host ""
Write-Host "Demo iniciada:"
Write-Host "- Orquestrador: http://localhost:8000"
Write-Host "- MCP:          http://localhost:8004/mcp"
Write-Host "- Streamlit:    http://localhost:8501"
Write-Host "- Logs:         $LogDir"

Start-Process "http://localhost:8501"

if ($NoWait) {
    Write-Host ""
    Write-Host "Serviços ficaram rodando em segundo plano."
    exit 0
}

Write-Host ""
Read-Host "Pressione Enter para encerrar a demo"

foreach ($item in $started) {
    if (-not $item.Process.HasExited) {
        Stop-Process -Id $item.Process.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Demo encerrada."
