# Restore local PostgreSQL dump to Neon using Docker (no need to install PostgreSQL on Windows).
#
# Prerequisites:
#   - Docker Desktop running
#   - Dump file exists (e.g. orbit.dump in project root or backend folder)
#
# Usage:
#   1. Put your dump file path in $DumpPath below (or pass as first argument).
#   2. Set your Neon connection string in $NeonUrl (or use env var NEON_DATABASE_URL).
#   3. Run: .\scripts\restore-to-neon.ps1
#
# Neon URL must be in libpq form (postgresql://...), NOT postgresql+asyncpg.

param(
    [string] $DumpPath = "",
    [string] $NeonUrl = $env:NEON_DATABASE_URL
)

if (-not $DumpPath) {
    # Try common locations
    $candidates = @(
        ".\orbit.dump",
        ".\backend\orbit.dump",
        "..\orbit.dump"
    )
    foreach ($c in $candidates) {
        $resolved = Resolve-Path -Path $c -ErrorAction SilentlyContinue
        if ($resolved) { $DumpPath = $resolved.Path; break }
    }
}

if (-not $DumpPath -or -not (Test-Path -LiteralPath $DumpPath)) {
    Write-Error "Dump file not found. Set DumpPath or pass it: .\scripts\restore-to-neon.ps1 -DumpPath 'C:\path\to\orbit.dump'"
    exit 1
}

# Use libpq URL (postgresql://...) for pg_restore; replace +asyncpg if you copied from backend env
$url = $NeonUrl -replace "\+asyncpg", ""
if (-not $url) {
    Write-Error "Set NEON_DATABASE_URL or pass -NeonUrl (e.g. postgresql://user:pass@host/neondb?sslmode=require)"
    exit 1
}

$dumpDir = [System.IO.Path]::GetDirectoryName($DumpPath)
$dumpName = [System.IO.Path]::GetFileName($DumpPath)

Write-Host "Restoring $DumpPath to Neon using Docker..."
# Pass URL via env to avoid escaping issues with & and ? in connection string
docker run --rm `
    -v "${dumpDir}:/dump:ro" `
    -e "NEON_URL=$url" `
    postgres:16-alpine `
    sh -c "pg_restore --no-owner --no-privileges --clean --if-exists -d \"\$NEON_URL\" \"/dump/$dumpName\""

if ($LASTEXITCODE -eq 0) {
    Write-Host "Restore finished successfully."
} else {
    Write-Host "Restore exited with code $LASTEXITCODE. Some errors (e.g. object already exists) may be safe to ignore if data is present."
}
