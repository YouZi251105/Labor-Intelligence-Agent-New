param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot "backups"))
$source = [IO.Path]::GetFullPath($BackupFile)
if (-not $source.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Backup file must stay under the project backups directory."
}
if (-not (Test-Path -LiteralPath $source)) {
    throw "Backup file not found: $source"
}

$databaseUrl = $env:DATABASE_URL
if (-not $databaseUrl) {
    $databaseUrl = "sqlite+aiosqlite:///./data/demo.db"
}

if ($source.EndsWith(".db", [StringComparison]::OrdinalIgnoreCase)) {
    if (-not $databaseUrl.StartsWith("sqlite")) {
        throw "SQLite backup cannot restore into a non-SQLite database."
    }
    $relative = $databaseUrl -replace "^sqlite\+aiosqlite:///", ""
    $target = [IO.Path]::GetFullPath((Join-Path (Join-Path $projectRoot "backend") $relative))
    if (Test-Path -LiteralPath $target) {
        $safety = "$target.before-restore"
        Copy-Item -LiteralPath $target -Destination $safety -Force
    }
    Copy-Item -LiteralPath $source -Destination $target -Force
    Write-Output "SQLite database restored to $target"
    exit 0
}

if ($source.EndsWith(".dump", [StringComparison]::OrdinalIgnoreCase)) {
    if (-not $databaseUrl.StartsWith("postgresql")) {
        throw "PostgreSQL backup cannot restore into a non-PostgreSQL database."
    }
    $pgRestore = Get-Command pg_restore -ErrorAction SilentlyContinue
    if (-not $pgRestore) {
        throw "pg_restore is required for PostgreSQL restores."
    }
    & $pgRestore.Source --dbname=$databaseUrl --clean --if-exists --no-owner $source
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore failed with exit code $LASTEXITCODE"
    }
    Write-Output "PostgreSQL backup restored."
    exit 0
}

throw "Unsupported backup file type."
