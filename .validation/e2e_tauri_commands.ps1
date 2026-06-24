# E2E smoke for the Tauri shell's pipe-server backend.
# Spawns flowntier-runtime.exe, then sends a sequence of JSON-RPC
# requests that exercise every Tauri command surface (mirrors
# what the React webview does via invoke()). Reports per-call
# status. Run after `cargo build` (release or debug) succeeds.
#
# Usage: powershell -File .validation/e2e_tauri_commands.ps1

$ErrorActionPreference = 'Stop'
$pipeName = 'flowntier_runtime'
$base = Join-Path $PSScriptRoot '..'

# Locate the runtime binary (prefer release, fall back to debug).
$runtimeExe = Join-Path $base 'target\release\flowntier-runtime.exe'
if (-not (Test-Path $runtimeExe)) {
    $runtimeExe = Join-Path $base 'target\debug\flowntier-runtime.exe'
}
if (-not (Test-Path $runtimeExe)) {
    Write-Error "runtime binary not found; run cargo build -p pipe-server first"
    exit 1
}

Write-Host "==> starting runtime: $runtimeExe"
$proc = Start-Process -FilePath $runtimeExe -PassThru -NoNewWindow -RedirectStandardError "$env:TEMP\flowntier-stderr.log"

# Wait up to 30s for the named pipe.
$deadline = (Get-Date).AddSeconds(30)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $c = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, 'InOut')
        $c.Connect(500)
        if ($c.IsConnected) { $ready = $true; $c.Close(); break }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ready) {
    Write-Error "sidecar did not open $pipeName within 30s"
    try { Stop-Process -Id $proc.Id -Force } catch {}
    exit 1
}
Write-Host "==> sidecar ready on \\.\pipe\$pipeName"

# JSON-RPC helper.
function Send-Rpc($id, $method, $path, $body = $null) {
    # PowerShell 5.1's ConvertTo-Json drops $null fields by
    # default, which would strip the 'body' key when callers pass
    # $null. Force the body to be an explicit JSON null in the
    # payload so the server always sees a complete request.
    $bodyField = if ($null -eq $body) { 'null' } else { ($body | ConvertTo-Json -Depth 10 -Compress) }
    $reqRaw = "{`"jsonrpc`":`"2.0`",`"id`":$id,`"method`":`"$method`",`"params`":{`"path`":`"$path`",`"body`":$bodyField}}"
    $c = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, 'InOut')
    $c.Connect(2000)
    $w = New-Object System.IO.StreamWriter($c)
    $r = New-Object System.IO.StreamReader($c)
    $w.NewLine = "`n"
    $w.WriteLine($reqRaw); $w.Flush()
    $line = $r.ReadLine()
    $c.Close()
    $line | ConvertFrom-Json
}

# Each test case: hashtable with n=label, method, path, body, expected-substring, optional err=expected-error, optional repeat
$tests = @(
    @{ n = '/api/ping (health)';          method = 'GET'; path = '/api/ping';                 body = $null;     ex = 'flowntier-rs' },
    @{ n = '/api/ping unknown method 404'; method = 'GET'; path = '/api/no-such-route';        body = $null;     ex = 'no handler'; expectError = $true },
    @{ n = '/api/providers';               method = 'GET'; path = '/api/providers';            body = $null;     ex = 'providers' },
    @{ n = '/api/router/roles';            method = 'GET'; path = '/api/router/roles';         body = $null;     ex = 'roles' },
    @{ n = '/api/router/models';           method = 'GET'; path = '/api/router/models';        body = $null;     ex = 'models' },
    @{ n = '/api/plugins';                 method = 'GET'; path = '/api/plugins';              body = $null;     ex = 'plugins' },
    @{ n = '/api/i_ching/draw';            method = 'GET'; path = '/api/i_ching/draw';         body = $null;     ex = 'draw' },
    @{ n = '/api/i_ching/draw x3';         method = 'GET'; path = '/api/i_ching/draw';         body = $null;     ex = 'draw';  repeat = 3 },
    @{ n = '/api/i_ching/list';            method = 'GET'; path = '/api/i_ching/list';         body = $null;     ex = 'list' },
    @{ n = '/api/run_task missing task';    method = 'POST'; path = '/api/run_task';             body = @{};       ex = 'task'; expectError = $true },
    @{ n = '/api/run_task missing base_url';method = 'POST'; path = '/api/run_task';             body = @{ task = 'hi' }; ex = 'base_url'; expectError = $true }
    @{ n = '/api/run_task unsupported provider'
       method = 'POST'
       path = '/api/run_task'
       body = @{
           task = 'hi'
           base_url = 'http://x'
           model = 'm'
           provider_kind = 'bogus'
       }
       ex = 'unsupported'
       expectError = $true }
)

$pass = 0; $fail = 0; $failList = @()
$id = 1
foreach ($t in $tests) {
    $rep = $t.repeat; if (-not $rep) { $rep = 1 }
    for ($k = 0; $k -lt $rep; $k++) {
        Write-Host ("==> [{0,-35}] " -f $t.n) -NoNewline
        try {
            $bodyArg = $null
            if ($null -ne $t.body) { $bodyArg = $t.body }
            Write-Host "  [debug] t.method='$($t.method)' t.path='$($t.path)'"
            $resp = Send-Rpc -id $id -method $t.method -path $t.path -body $bodyArg
            $id++
            $rawJson = $resp | ConvertTo-Json -Depth 10 -Compress
            Write-Host "  [debug] raw: $rawJson"
            if ($t.expectError) {
                # expect an error envelope
                if ($resp.error -or $rawJson -match 'error') {
                    Write-Host "PASS (error as expected)"
                    $pass++
                } else {
                    Write-Host "FAIL (expected error but got success): $rawJson"
                    $fail++; $failList += $t.n
                }
            } else {
                # Match against the result.body, not the whole raw JSON
                # (the whole JSON contains substrings like 'no handler
                # registered for path "/api/roles"' that would falsely
                # match 'roles'). Serialize the body to a compact
                # string first.
            $bodyJson = ''
            if ($resp.result) {
                # Serialize the whole result object (with body nested
                # under it). PowerShell's property access is
                # awkward here because the parsed RpcResponse has
                # .result.{status, body} as a nested object, and
                # naive -Depth 1 in ConvertTo-Json drops .body.
                $bodyJson = $resp.result | ConvertTo-Json -Depth 10 -Compress
            }
            if ($bodyJson -match $t.ex) {
                Write-Host "PASS"
                $pass++
            } else {
                Write-Host "FAIL (expected match '$($t.ex)' in result, got: $bodyJson)"
                $fail++; $failList += $t.n
            }
            }
        } catch {
            Write-Host "EXCEPTION: $_"
            $fail++; $failList += $t.n
        }
    }
}

Write-Host ""
Write-Host "=================="
Write-Host "PASS: $pass"
Write-Host "FAIL: $fail"
if ($fail -gt 0) {
    Write-Host "Failed cases:"
    $failList | ForEach-Object { Write-Host "  - $_" }
}

# Cleanup.
try { Stop-Process -Id $proc.Id -Force } catch {}
if ($fail -gt 0) { exit 1 }