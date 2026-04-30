param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonRoot = Split-Path -Parent $PythonExe
$CondaLibraryBin = Join-Path $PythonRoot "Library\bin"
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
    opencv-python `
    numpy

$PyInstallerArgs = @(
    "--clean",
    "--noconfirm",
    "--onedir",
    "--name", "KinectDepthCameraValidation",
    "--paths", $BuildPackages,
    "--collect-binaries", "cv2",
    "--exclude-module", "tkinter",
    "--exclude-module", "PyQt5",
    "--exclude-module", "PySide6",
    "--exclude-module", "matplotlib",
    "--exclude-module", "IPython",
    "--exclude-module", "numba"
)

if (Test-Path -LiteralPath $CondaLibraryBin) {
    $CondaDlls = @(
        "ffi.dll",
        "libcrypto-3-x64.dll",
        "libssl-3-x64.dll",
        "libbz2.dll",
        "libexpat.dll"
    )

    foreach ($DllName in $CondaDlls) {
        $DllPath = Join-Path $CondaLibraryBin $DllName
        if (Test-Path -LiteralPath $DllPath) {
            $PyInstallerArgs += @("--add-binary", "$DllPath;.")
        }
    }
}

$PyInstallerArgs += "main.py"

& $PythonExe -m PyInstaller @PyInstallerArgs

Write-Host ""
Write-Host "Build complete:"
Write-Host (Join-Path $ProjectRoot "dist\KinectDepthCameraValidation\KinectDepthCameraValidation.exe")
