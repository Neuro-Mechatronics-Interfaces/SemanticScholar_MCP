<#
.SYNOPSIS
    Rebuild and validate the SemanticScholar_MCP development installation.

.DESCRIPTION
    Reinstalls SemanticScholar_MCP in editable development mode.

    By default, the script:
      1. Cleans stale pip installation artifacts.
      2. Upgrades pip.
      3. Installs the package with development dependencies.
      4. Runs pytest.
      5. Runs `ruff check .`.
      6. Increments the package patch version.
      7. Refreshes the editable installation with the new version.
      8. Reports the installed package version.

    Tests and linting must pass before the automatic patch increment occurs.

.PARAMETER SkipVersionIncrement
    Rebuild without automatically incrementing the patch version.

    This is used by version.ps1 after an explicit major, minor, or patch
    version increment has already been performed.

.PARAMETER NoTest
    Skip both pytest and Ruff validation.

    This option is ignored when -TestIntegration is also specified.

.PARAMETER TestIntegration
    Run the test suite with live Semantic Scholar integration tests by invoking:

        pytest --run-integration

    Ruff is also run.

    This switch takes precedence over -NoTest.

.EXAMPLE
    .\rebuild.ps1

    Performs a normal rebuild, runs pytest and Ruff, and increments the
    patch version after validation succeeds.

.EXAMPLE
    .\rebuild.ps1 -NoTest

    Rebuilds without running pytest or Ruff. The patch version is still
    incremented.

.EXAMPLE
    .\rebuild.ps1 -TestIntegration

    Rebuilds using the full test suite, including live Semantic Scholar
    integration tests, then runs Ruff and increments the patch version.

.EXAMPLE
    .\rebuild.ps1 -SkipVersionIncrement

    Rebuilds and validates the project without changing its version.

.EXAMPLE
    .\rebuild.ps1 -SkipVersionIncrement -NoTest

    Rebuilds without testing, linting, or changing the package version.

.EXAMPLE
    .\rebuild.ps1 -NoTest -TestIntegration

    Runs integration tests and Ruff because -TestIntegration takes
    precedence over -NoTest.

.NOTES
    For explicit semantic-version changes, use version.ps1:

        .\version.ps1 patch
        .\version.ps1 minor
        .\version.ps1 major

    version.ps1 invokes rebuild.ps1 with -SkipVersionIncrement to avoid
    incrementing the patch version twice.
#>

[CmdletBinding()]
param(
    [switch]$SkipVersionIncrement,
    [switch]$NoTest,
    [switch]$TestIntegration
)

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$versionScript = Join-Path $repoRoot "version.ps1"
$sitePackages = Join-Path $repoRoot ".venv\Lib\site-packages"
$scriptsDir = Join-Path $repoRoot ".venv\Scripts"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found: $venvPython"
}

if (-not $SkipVersionIncrement -and -not (Test-Path $versionScript)) {
    throw "version.ps1 not found: $versionScript"
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,

        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

Push-Location $repoRoot

try {
    #
    # Clean stale artifacts from interrupted pip installs.
    #
    if (Test-Path $sitePackages) {
        Get-ChildItem $sitePackages |
            Where-Object { $_.Name -like "~emantic*" } |
            Remove-Item -Recurse -Force
    }

    if (Test-Path $scriptsDir) {
        Get-ChildItem $scriptsDir -Filter "*.deleteme" |
            Remove-Item -Force
    }

    #
    # Establish/update the development environment before testing.
    #
    Write-Host ""
    Write-Host "Updating development environment..."

    Invoke-Checked `
        -Description "pip upgrade" `
        -Command {
            & $venvPython -m pip install --upgrade pip
        }

    Invoke-Checked `
        -Description "Editable package installation" `
        -Command {
            & $venvPython -m pip install -e ".[dev]"
        }

    #
    # Test / lint gate.
    #
    # -TestIntegration explicitly supersedes -NoTest.
    #
    $runValidation = (-not $NoTest) -or $TestIntegration

    if ($runValidation) {
        Write-Host ""

        if ($TestIntegration) {
            Write-Host "Running pytest with live integration tests..."

            Invoke-Checked `
                -Description "Integration test suite" `
                -Command {
                    & $venvPython -m pytest --run-integration
                }
        }
        else {
            Write-Host "Running pytest..."

            Invoke-Checked `
                -Description "Test suite" `
                -Command {
                    & $venvPython -m pytest
                }
        }

        Write-Host ""
        Write-Host "Running Ruff..."

        Invoke-Checked `
            -Description "Ruff lint check" `
            -Command {
                & $venvPython -m ruff check .
            }
    }
    else {
        Write-Host ""
        Write-Host "Skipping tests and Ruff (-NoTest)."
    }

    #
    # Automatic patch increment.
    #
    # This happens only after validation succeeds.
    #
    if (-not $SkipVersionIncrement) {
        Write-Host ""
        Write-Host "Incrementing patch version..."

        & $versionScript patch -NoRebuild

        if ($LASTEXITCODE -ne 0) {
            throw "Version increment failed with exit code $LASTEXITCODE."
        }

        #
        # Refresh package metadata after pyproject.toml changed.
        #
        # Dependencies were already resolved above, so --no-deps is sufficient.
        #
        Write-Host ""
        Write-Host "Refreshing editable installation with new version..."

        Invoke-Checked `
            -Description "Version metadata refresh" `
            -Command {
                & $venvPython -m pip install --no-deps -e .
            }
    }
    else {
        Write-Host ""
        Write-Host "Version increment skipped."
    }

    #
    # Verify installed metadata.
    #
    $installedVersion = & $venvPython -c `
        "from importlib.metadata import version; print(version('semantic-scholar-mcp'))"

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to verify installed semantic-scholar-mcp version."
    }

    $sourceVersion = & $venvPython -c `
        "import semantic_scholar_mcp; print(semantic_scholar_mcp.__version__)"

    if ($LASTEXITCODE -ne 0) {
        throw "Unable to verify semantic_scholar_mcp.__version__."
    }

    Write-Host ""
    Write-Host "Rebuild complete."
    Write-Host "Installed package version: $installedVersion"
    Write-Host "Imported package version:  $sourceVersion"
}
finally {
    Pop-Location
}