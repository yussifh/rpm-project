Set-Location "$PSScriptRoot\backend"
Invoke-Expression "$PSScriptRoot\backend\venv\Scripts\Activate.ps1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000