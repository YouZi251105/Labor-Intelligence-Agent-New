param(
    [string]$OutputDirectory = "backups"
)

$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outputPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $OutputDirectory))
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot "backups"))
if (-not $outputPath.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Backup output must stay under the project backups directory."
}
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$databaseUrl = $env:DATABASE_URL
if (-not $databaseUrl) {
    $databaseUrl = "sqlite+aiosqlite:///./data/demo.db"
}

if ($databaseUrl.StartsWith("sqlite")) {
    $relative = $databaseUrl -replace "^sqlite\+aiosqlite:///", ""
    $source = [IO.Path]::GetFullPath((Join-Path (Join-Path $projectRoot "backend") $relative))
    if (-not (Test-Path -LiteralPath $source)) {
        throw "SQLite database not found: $source"
    }
    $target = Join-Path $outputPath "sqlite-$timestamp.db"
    Copy-Item -LiteralPath $source -Destination $target
    Write-Output "SQLite backup written to $target"
    exit 0
}

if ($databaseUrl.StartsWith("postgresql")) {
    $pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
    if (-not $pgDump) {
        throw "pg_dump is required for PostgreSQL backups."
    }
    $target = Join-Path $outputPath "postgres-$timestamp.dump"
    & $pgDump.Source --dbname=$databaseUrl --format=custom --file=$target
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump failed with exit code $LASTEXITCODE"
    }
    Write-Output "PostgreSQL backup written to $target"
    exit 0
}

throw "Unsupported DATABASE_URL scheme."
