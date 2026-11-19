$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$ProjectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path $ProjectPython)) {
    throw 'Execute .\instalar_gs.ps1 antes de abrir o menu.'
}
$env:PYTHONUTF8 = '1'
function Run-Module {
    & $ProjectPython -m @args
    if ($LASTEXITCODE -ne 0) { Write-Warning "Operação interrompida, código $LASTEXITCODE." }
}
do {
    Write-Host @"
VivaBairro Voz — Global Solution
 1 Ambiente, testes e HTTP       7 Importar ficha(s) TTS
 2 Pendências acadêmicas         8 Comparação A/B offline
 3 Importar áudios G08–G14        9 Importar turno ou verificar E2E
 4 Revisão cega / importar JSON  10 Gerar relatório preliminar
 5 Rodada STT paga autorizada   11 Simular entrega final
 6 Recalcular métricas e WER    12 Preparar artefatos finais
 0 Sair
"@
    $choice = Read-Host 'Opção'
    try {
        switch ($choice) {
            '1' {
                & $ProjectPython scripts/verify.py --ui --evidence ("evaluation/results/verificacao_" + (Get-Date -Format yyyyMMdd_HHmmssff) + ".json")
                if (Get-Command node -ErrorAction SilentlyContinue) { & node --test tests/latency.test.mjs }
                else { Write-Warning 'Instale Node.js para a suíte JavaScript.' }
            }
            '2' { Run-Module scripts.gs_preflight --dry-run }
            '3' { $source = Read-Host 'Pasta com os originais de Gustavo'; if ($source) { Run-Module evaluation.importar_gustavo $source } }
            '4' {
                $review = Read-Host 'Caminho do JSON exportado, ou Enter para abrir a página de revisão'
                if ($review) { Run-Module evaluation.run_stt --importar-revisao $review }
                else {
                    & $ProjectPython -m evaluation.run_stt
                    if ($LASTEXITCODE -eq 0) { Invoke-Item -LiteralPath 'evaluation/results/stt_revisao.html' }
                }
            }
            '5' {
                & $ProjectPython -m evaluation.run_stt
                if ($LASTEXITCODE -ne 0) { break }
                $ready = @(Import-Csv 'evaluation/results/stt_resultados_parciais.csv' | Where-Object stt_status -eq 'PENDENTE_AUTORIZACAO_API')
                if (-not $ready.Count) { Write-Host 'Nenhuma gravação nova com consentimento vinculado.'; break }
                $ids = @($ready | ForEach-Object sample_id)
                $seconds = ($ready | ForEach-Object { [Math]::Ceiling([double]::Parse($_.prepared_seconds, [Globalization.CultureInfo]::InvariantCulture)) } | Measure-Object -Sum).Sum
                $cost = [Math]::Round($seconds * 0.0045 / 60, 6)
                Write-Host "OpenAI gpt-transcribe. Até $($ids.Count) chamadas para $($ids -join ', '). Estimativa USD $cost."
                if ((Read-Host 'Se você tem autorização de custo, digite AUTORIZO STT') -eq 'AUTORIZO STT') {
                    Run-Module evaluation.run_stt --autorizar-api $ids.Count --ids @ids
                }
            }
            '6' { Run-Module evaluation.academic_metrics --saida ("evaluation/results/metricas_" + (Get-Date -Format yyyyMMdd_HHmmssff)) }
            '7' {
                $notes = Read-Host 'Pasta contendo somente os CSVs devolvidos pelos avaliadores'
                if ($notes) {
                    $fichas = @(Get-ChildItem -LiteralPath $notes -File -Filter 'avaliacao_tts_*.csv' | ForEach-Object FullName)
                    if ($fichas.Count) { Run-Module evaluation.importar_notas_tts @fichas --graficos ("evaluation/results/tts_notas_" + (Get-Date -Format yyyyMMdd_HHmmssff)) }
                    else { Write-Host 'Nenhuma ficha encontrada.' }
                }
            }
            '8' {
                $exe = 'tools/whisper/bin/Release/whisper-cli.exe'
                if (Test-Path $exe) { Run-Module evaluation.compare_stt $exe 'tools/whisper/ggml-base-q5_1.bin' }
                else { Write-Host 'Execute .\preparar_whisper.ps1 primeiro. A coleta depende de referências humanas revisadas.' }
            }
            '9' {
                $capture = Read-Host 'Caminho do JSON de captura, ou Enter para exibir pendências'
                if ($capture) { Run-Module evaluation.import_e2e $capture }
                Run-Module scripts.gs_preflight --dry-run
            }
            '10' { Run-Module scripts.finalizar_gs --preliminar --saida ("entrega_gs_preliminar_" + (Get-Date -Format yyyyMMdd_HHmmssff)) }
            '11' { Run-Module scripts.finalizar_gs --dry-run }
            '12' {
                $edition = Read-Host 'Edição confirmada pelo docente'
                $scope = Read-Host 'Caminho do JSON de escopo para o professor'
                $decision = Read-Host 'Caminho do TXT com a justificativa da escolha STT'
                if ($edition -and $scope -and $decision) {
                    Run-Module scripts.finalizar_gs --saida ("entrega_gs_final_" + (Get-Date -Format yyyyMMdd_HHmmssff)) --edicao $edition --escopo $scope --decisao $decision
                } else { Write-Host 'Edição, escopo e justificativa são necessários para finalizar.' }
            }
        }
    } catch { Write-Warning $_.Exception.Message }
} while ($choice -ne '0')
