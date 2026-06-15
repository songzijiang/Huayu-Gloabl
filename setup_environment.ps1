[CmdletBinding()]
param(
    [string]$EnvironmentName = "huayu-global"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$pythonVersion = "3.11.9"
$pipVersion = "23.2.1"
$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"

function Invoke-Conda {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    & conda @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Conda command failed: conda $($Arguments -join ' ')"
    }
}

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "Conda was not found. Install Miniconda or Anaconda, then reopen PowerShell."
}

if (-not (Test-Path -LiteralPath $requirementsPath -PathType Leaf)) {
    throw "requirements.txt was not found at $requirementsPath"
}

Write-Host "Preparing Conda environment '$EnvironmentName'..."

$environmentJson = & conda env list --json
if ($LASTEXITCODE -ne 0) {
    throw "Unable to query Conda environments."
}

$environmentJsonText = $environmentJson -join [Environment]::NewLine
$environmentPaths = @(($environmentJsonText | ConvertFrom-Json).envs)
$environmentExists = $environmentPaths |
    Where-Object { (Split-Path -Leaf $_) -eq $EnvironmentName } |
    Select-Object -First 1

if (-not $environmentExists) {
    Invoke-Conda @(
        "create",
        "-n", $EnvironmentName,
        "python=$pythonVersion",
        "pip=$pipVersion",
        "-y"
    )
} else {
    Write-Host "Environment already exists; pinned packages will be refreshed."
    Invoke-Conda @(
        "install",
        "-n", $EnvironmentName,
        "python=$pythonVersion",
        "pip=$pipVersion",
        "-y"
    )
}

Write-Host "Installing compiled geospatial dependencies..."
Invoke-Conda @(
    "install",
    "-n", $EnvironmentName,
    "-c", "conda-forge",
    "gdal=3.6.2",
    "rasterio=1.3.9",
    "cartopy=0.22.0",
    "pyproj=3.7.2",
    "shapely=2.0.5",
    "h5py=3.10.0",
    "netcdf4=1.6.4",
    "-y"
)

Write-Host "Installing the pinned Python package snapshot..."
Invoke-Conda @(
    "run",
    "-n", $EnvironmentName,
    "python", "-m", "pip",
    "install", "-r", $requirementsPath
)

Write-Host "Verifying dependencies and core imports..."
Invoke-Conda @(
    "run",
    "-n", $EnvironmentName,
    "python", "-m", "pip", "check"
)
Invoke-Conda @(
    "run",
    "-n", $EnvironmentName,
    "python", "-c",
    "import jacksung, numpy, scipy, rasterio, PIL, torch; print(f'Python environment OK; PyTorch={torch.__version__}; CUDA={torch.version.cuda}; CUDA available={torch.cuda.is_available()}')"
)

Write-Host ""
Write-Host "Environment setup complete."
Write-Host "Run inference with:"
Write-Host "conda run -n $EnvironmentName python HuayuGlobal.py"
