param(
    [int[]]$Ports = @(8000, 8001, 8002, 8003, 8004)
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Write-Error "Arquivo .env não encontrado. Copie .env.example para .env e configure sua GROQ_API_KEY."
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

function Start-HiddenService {
    param(
        [string]$Name,
        [string]$Arguments
    )

    Write-Host "==> Iniciando $Name..."
    Start-Process -FilePath "python" -ArgumentList $Arguments -WindowStyle Hidden
}

Start-HiddenService "Agente Resumidor (porta 8001)" "-m uvicorn agents.summarizer_agent:app --port 8001 --log-level warning"
Start-HiddenService "Agente de Sentimento (porta 8002)" "-m uvicorn agents.sentiment_agent:app --port 8002 --log-level warning"
Start-HiddenService "Agente Categorizador (porta 8003)" "-m uvicorn agents.categorizer_agent:app --port 8003 --log-level warning"
Start-HiddenService "Orquestrador (porta 8000)" "-m uvicorn orchestrator.main:app --port 8000 --log-level warning"

Write-Host "==> Iniciando servidor MCP (porta 8004 /mcp)..."
Start-Process -FilePath "powershell" `
    -ArgumentList "-NoProfile -Command `$env:MCP_TRANSPORT='streamable-http'; `$env:MCP_PORT='8004'; python mcp_server.py" `
    -WindowStyle Hidden

Start-Sleep -Seconds 3

Write-Host "==> Iniciando interface Streamlit..."
Start-Process -FilePath "python" -ArgumentList "-m streamlit run app.py" -WindowStyle Hidden

Write-Host ""
Write-Host "Demo iniciada:"
Write-Host "- Orquestrador: http://localhost:8000"
Write-Host "- MCP:          http://localhost:8004/mcp"
Write-Host "- Streamlit:    http://localhost:8501"
