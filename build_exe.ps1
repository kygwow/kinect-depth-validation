param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildPackages = Join-Path $ProjectRoot ".build-packages"
$PipTemp = Join-Path $ProjectRoot ".pip-build-tmp"
$SiteCustomize = Join-Path $ProjectRoot ".pip-sitecustomize"

New-Item -ItemType Directory -Force -Path $BuildPackages | Out-Null
New-Item -ItemType Directory -Force -Path $PipTemp | Out-Null

$env:TEMP = $PipTemp
$env:TMP = $PipTemp
$env:PYTHONPATH = "$SiteCustomize;$BuildPackages"

& $PythonExe -m pip install --target $BuildPackages --upgrade --no-cache-dir --no-build-isolation `
    pyinstaller `
    pyk4a `
    opencv-python `
    numpy

& $PythonExe -m PyInstaller `
    --clean `
    --noconfirm `
    --onedir `
    --name "KinectDepthCameraValidation" `
    --paths $BuildPackages `
    --hidden-import pyk4a `
    --hidden-import k4a_module `
    --collect-submodules pyk4a `
    --collect-binaries pyk4a `
    --collect-data pyk4a `
    --collect-binaries cv2 `
    --exclude-module tkinter `
    --exclude-module PyQt5 `
    --exclude-module PySide6 `
    --exclude-module matplotlib `
    --exclude-module IPython `
    --exclude-module numba `
    main.py

Write-Host ""
Write-Host "Build complete:"
Write-Host (Join-Path $ProjectRoot "dist\KinectDepthCameraValidation\KinectDepthCameraValidation.exe")
