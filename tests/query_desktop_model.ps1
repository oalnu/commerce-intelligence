param(
    [Parameter(Mandatory=$true)][string]$QueryFile,
    [Parameter(Mandatory=$true)][string]$OutputFile,
    [switch]$PrintRows
)
$ErrorActionPreference = 'Stop'
[System.Reflection.Assembly]::LoadFrom('C:\Program Files\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll') | Out-Null
$portFile = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces" -Filter msmdsrv.port.txt -Recurse |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $portFile) { throw 'No running Desktop model port was found.' }
$port = (Get-Content -LiteralPath $portFile.FullName -Encoding Unicode -Raw).Trim()
$connection = [Microsoft.AnalysisServices.AdomdClient.AdomdConnection]::new("Data Source=localhost:$port")
try {
    $connection.Open()
    $catalogs = $connection.GetSchemaDataSet('DBSCHEMA_CATALOGS', $null)
    if ($catalogs.Tables[0].Rows.Count -ne 1) { throw 'Expected exactly one loaded model in the newest Desktop engine.' }
    $catalogName = [string]$catalogs.Tables[0].Rows[0]['CATALOG_NAME']
    $connection.ChangeDatabase($catalogName)
    $command = $connection.CreateCommand()
    $command.CommandTimeout = 120
    $command.CommandText = Get-Content -LiteralPath $QueryFile -Raw
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $reader = $command.ExecuteReader()
    $rows = @()
    while ($reader.Read()) {
        $record = [ordered]@{}
        for ($i=0; $i -lt $reader.FieldCount; $i++) {
            $record[$reader.GetName($i)] = if ($reader.IsDBNull($i)) { $null } else { $reader.GetValue($i) }
        }
        $rows += [pscustomobject]$record
    }
    $reader.Close()
    $timer.Stop()
    [ordered]@{checked_utc=[DateTime]::UtcNow.ToString('o');query_seconds=$timer.Elapsed.TotalSeconds;rows=@($rows)} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputFile -Encoding utf8
    Write-Output "Query completed: $($rows.Count) rows; $([math]::Round($timer.Elapsed.TotalSeconds,3)) seconds. Saved $OutputFile"
    if ($PrintRows) { Get-Content -LiteralPath $OutputFile -Raw }
} finally { $connection.Dispose() }
