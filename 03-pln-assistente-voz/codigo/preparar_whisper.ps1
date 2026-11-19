param([string]$CacheDir)
$ErrorActionPreference = 'Stop'
$destination = Join-Path $PSScriptRoot 'tools/whisper'
$zipHash = 'b07ea0b1b4115a38e1a7b07debf581f0b77d999925f8acb8f39d322b0ba0a822'
$modelHash = '422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898'
$engineHash = '111bd344b7bf0356818f2795a525cb5240ed0a99028fa9f3f1c68b4ff5b17b91'
function Confirm-Hash($Path, $Expected) {
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ne $Expected) {
        throw "SHA-256 divergente em $Path"
    }
}
if (Test-Path -LiteralPath $destination) {
    Confirm-Hash (Join-Path $destination 'bin/Release/whisper-cli.exe') $engineHash
    Confirm-Hash (Join-Path $destination 'ggml-base-q5_1.bin') $modelHash
    Write-Output 'Whisper já preparado e conferido.'
    exit 0
}
$parent = Split-Path -Parent $destination
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$stage = Join-Path $parent ('whisper-instalar-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
$zip = Join-Path $stage 'whisper-bin-x64.zip'
$model = Join-Path $stage 'ggml-base-q5_1.bin'
if ($CacheDir) {
    Copy-Item -LiteralPath (Join-Path $CacheDir 'whisper-bin-x64.zip') -Destination $zip
    Copy-Item -LiteralPath (Join-Path $CacheDir 'ggml-base-q5_1.bin') -Destination $model
} else {
    Invoke-WebRequest -Uri 'https://github.com/ggml-org/whisper.cpp/releases/download/v1.8.6/whisper-bin-x64.zip' -OutFile $zip
    Invoke-WebRequest -Uri 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q5_1.bin' -OutFile $model
}
Confirm-Hash $zip $zipHash
Confirm-Hash $model $modelHash
Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $stage 'bin')
Confirm-Hash (Join-Path $stage 'bin/Release/whisper-cli.exe') $engineHash
Remove-Item -LiteralPath $zip
Move-Item -LiteralPath $stage -Destination $destination
Write-Output 'Whisper v1.8.6 e os pesos foram conferidos e instalados localmente.'
