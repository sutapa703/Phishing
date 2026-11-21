$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$port = 8080

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating Python 3.12 environment..."

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python is not installed. Install Python 3.12 or run: winget install -e --id Python.Python.3.12"
    }

    & $python.Source -m pip install --disable-pip-version-check --quiet uv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install uv."
    }

    & $python.Source -m uv venv --python 3.12 $PSScriptRoot\.venv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python 3.12 environment."
    }
}

Write-Host "Installing dependencies..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python is not available. Install Python 3.12 or run: winget install -e --id Python.Python.3.12"
}

& $python.Source -m uv pip install --python $venvPython -r $PSScriptRoot\requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Could not install project dependencies."
}

while ($true) {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $tcpClient.BeginConnect("127.0.0.1", $port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(150, $false)) {
            break
        }
        $tcpClient.EndConnect($async)
        $port++
    }
    catch {
        break
    }
    finally {
        $tcpClient.Dispose()
    }
}

Write-Host "Starting the app at http://127.0.0.1:$port"
$env:PORT = "$port"
& $venvPython app.py
