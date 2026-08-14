# Download Microsoft WebView2 Fixed Version (x64) into vendor\WebView2Runtime
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VendorRuntime = Join-Path $Root "vendor\WebView2Runtime"
$Cache = Join-Path $Root "vendor\cache"
$PkgId = "webview2.runtime.x64"
$Ver = "150.0.4078.65"
$Nupkg = Join-Path $Cache "WebView2.Runtime.X64.$Ver.nupkg"
$Url = "https://api.nuget.org/v3-flatcontainer/$PkgId/$Ver/$PkgId.$Ver.nupkg"
$Marker = Join-Path $VendorRuntime "msedgewebview2.exe"

New-Item -ItemType Directory -Force -Path $Cache | Out-Null

if ((Test-Path $Marker)) {
    Write-Host "==> WebView2 Fixed Runtime already present: $VendorRuntime"
    exit 0
}

Write-Host "==> Download WebView2 Fixed Runtime $Ver"
python -c @"
import urllib.request, zipfile, shutil
from pathlib import Path
nupkg = Path(r'$Nupkg')
url = r'$Url'
vendor = Path(r'$VendorRuntime')
print('Downloading', url)
urllib.request.urlretrieve(url, nupkg)
print('size', nupkg.stat().st_size)
extract = nupkg.parent / 'extract_$Ver'
if extract.exists():
    shutil.rmtree(extract)
extract.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(nupkg) as z:
    z.extractall(extract)
src = extract / 'contentFiles' / 'any' / 'any' / 'WebView2'
if not (src / 'msedgewebview2.exe').is_file():
    raise SystemExit('msedgewebview2.exe missing in package')
if vendor.exists():
    shutil.rmtree(vendor)
shutil.copytree(src, vendor)
print('Installed to', vendor)
"@

if (-not (Test-Path $Marker)) {
    throw "Failed to prepare WebView2 runtime at $VendorRuntime"
}

Write-Host "==> WebView2 Fixed Runtime ready: $VendorRuntime"
