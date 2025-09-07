# PowerShell script to build the Windows executable via PyInstaller

if (!(Test-Path .venv)) {
  Write-Host "Creating virtual environment..."
  py -3 -m venv .venv
}

Write-Host "Activating virtual environment..."
. .venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host "Building executable..."
python build_exe.py
