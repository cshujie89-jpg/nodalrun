$ErrorActionPreference = "Stop"

Set-Location (Resolve-Path "$PSScriptRoot\..")

Write-Host "NodalRun final acceptance"
python -m py_compile apps\api\main.py runtime_core\store.py runtime_core\workspace.py runtime_core\remote_client.py workers\local_worker.py workers\remote_worker.py scripts\smoke_test.py scripts\remote_pm_demo.py
node --check apps\api\static\app.js
python scripts\smoke_test.py

Write-Host "NodalRun final acceptance passed"
