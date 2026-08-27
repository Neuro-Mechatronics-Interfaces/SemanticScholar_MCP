<#
.SYNOPSIS
    Increment the SemanticScholar_MCP semantic version.

.DESCRIPTION
    Updates the package version in pyproject.toml according to semantic
    versioning rules.

    Patch increment:
        0.1.0 -> 0.1.1

    Minor increment:
        0.1.7 -> 0.2.0

    Major increment:
        0.8.4 -> 1.0.0

    Unless -NoRebuild is specified, version.ps1 automatically invokes:

        .\rebuild.ps1 -SkipVersionIncrement

    after changing the version. This prevents rebuild.ps1 from applying an
    additional automatic patch increment.

.PARAMETER Part
    Specifies which portion of the semantic version to increment.

    Valid values are:

        patch
            Increment the patch number only.

            Example:
                0.1.4 -> 0.1.5

        minor
            Increment the minor number and reset patch to zero.

            Example:
                0.1.4 -> 0.2.0

        major
            Increment the major number and reset minor and patch to zero.

            Example:
                0.9.4 -> 1.0.0

.PARAMETER NoRebuild
    Update pyproject.toml without invoking rebuild.ps1.

    This is useful when another script is managing the build operation or
    when only the version metadata should be changed.

.EXAMPLE
    .\version.ps1 patch

    Increments the patch version and rebuilds the project.

    For example:

        0.1.4 -> 0.1.5

.EXAMPLE
    .\version.ps1 minor

    Increments the minor version, resets patch to zero, and rebuilds.

    For example:

        0.1.7 -> 0.2.0

.EXAMPLE
    .\version.ps1 major

    Increments the major version, resets minor and patch to zero, and rebuilds.

    For example:

        0.8.4 -> 1.0.0

.EXAMPLE
    .\version.ps1 patch -NoRebuild

    Increments the patch version without rebuilding.

.EXAMPLE
    .\version.ps1 minor -NoRebuild

    Increments the minor version and resets patch to zero without rebuilding.

.NOTES
    pyproject.toml is the authoritative source of the package version.

    Normal development rebuilds should generally use:

        .\rebuild.ps1

    which automatically increments the patch version after tests and linting
    succeed.

    Use version.ps1 when explicitly changing the semantic version level.
#>

[CmdletBinding()]
param(
    [Parameter(
        Mandatory = $true,
        Position = 0
    )]
    [ValidateSet("major", "minor", "patch")]
    [string]$Part,

    [switch]$NoRebuild
)

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$pyprojectPath = Join-Path $repoRoot "pyproject.toml"
$rebuildPath = Join-Path $repoRoot "rebuild.ps1"

if (-not (Test-Path $pyprojectPath)) {
    throw "pyproject.toml not found: $pyprojectPath"
}

# Read as one string so we can safely identify the [project] section.
$content = [System.IO.File]::ReadAllText($pyprojectPath)

# Capture:
#   1. [project] section up to the version value
#   2. major
#   3. minor
#   4. patch
#   5. remainder of the version line
#
# The lookahead prevents this from accidentally matching a version field
# from another TOML section.
$pattern = '(?ms)(^\[project\]\s*.*?^version\s*=\s*")(\d+)\.(\d+)\.(\d+)(".*?$)(?=.*?(?:^\[|\z))'

$match = [regex]::Match($content, $pattern)

if (-not $match.Success) {
    throw 'Could not find a semantic version such as version = "0.1.0" in the [project] section.'
}

$major = [int]$match.Groups[2].Value
$minor = [int]$match.Groups[3].Value
$patch = [int]$match.Groups[4].Value

$oldVersion = "$major.$minor.$patch"

switch ($Part) {
    "major" {
        $major++
        $minor = 0
        $patch = 0
    }

    "minor" {
        $minor++
        $patch = 0
    }

    "patch" {
        $patch++
    }
}

$newVersion = "$major.$minor.$patch"

$replacement =
    $match.Groups[1].Value +
    $newVersion +
    $match.Groups[5].Value

$newContent =
    $content.Substring(0, $match.Index) +
    $replacement +
    $content.Substring($match.Index + $match.Length)

# Write UTF-8 without BOM.
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText(
    $pyprojectPath,
    $newContent,
    $utf8NoBom
)

Write-Host "Version: $oldVersion -> $newVersion"

if (-not $NoRebuild) {
    if (-not (Test-Path $rebuildPath)) {
        throw "rebuild.ps1 not found: $rebuildPath"
    }

    Write-Host "Rebuilding semantic-scholar-mcp $newVersion..."

    & $rebuildPath -SkipVersionIncrement

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}