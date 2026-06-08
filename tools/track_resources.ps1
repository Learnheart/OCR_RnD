<#
.SYNOPSIS
    Theo dõi tài nguyên (RAM / WSL / VRAM GPU / CPU) cho từng giải pháp trong RnD_pipeline
    và ghi báo cáo Markdown + CSV vào results/resources/ của giải pháp đó.

.DESCRIPTION
    Shared tool cho workspace RnD (xem ../CLAUDE.md). Ba chế độ:

      1) Snapshot (mặc định)  : chụp 1 lần trạng thái máy + đánh giá "có phù hợp để chạy không".
      2) Monitor theo thời gian: -DurationSec N  -> lấy mẫu mỗi -IntervalSec giây trong N giây
                                 (chạy giải pháp ở terminal khác trong lúc này).
      3) Wrap-and-measure     : -Command "<lệnh>" -> chạy lệnh đó, lấy mẫu tới khi nó kết thúc,
                                 báo cáo kèm wall-time + exit code.

    Báo cáo gồm: thông tin máy, bảng tổng hợp min/avg/peak từng chỉ số, chi tiết GPU,
    tiến trình ngốn RAM lúc đỉnh, tiến trình đang giữ VRAM, và phần ĐÁNH GIÁ (verdict)
    so với ngưỡng để biết máy có an toàn để chạy hay sắp OOM.

.PARAMETER Solution
    Tên thư mục giải pháp dưới RnD_pipeline/ (hybrid | end-to-end-VLM | traditional).

.PARAMETER Command
    (tùy chọn) Lệnh PowerShell để chạy-và-đo. Khi có cờ này -> chế độ wrap-and-measure.

.PARAMETER DurationSec
    (tùy chọn) Số giây theo dõi khi KHÔNG truyền -Command. 0 = chỉ snapshot 1 lần.

.PARAMETER IntervalSec
    Khoảng lấy mẫu (giây). Mặc định 2.

.PARAMETER Label
    Nhãn ngắn cho lần đo (vd "M2-omnidocbench-100p"). Đi vào tên file báo cáo.

.PARAMETER Note
    Ghi chú tự do, in vào báo cáo.

.PARAMETER WatchProcess
    Danh sách pattern tên tiến trình cần cộng dồn RAM (mặc định: python, LM Studio, llama, vllm, docker, vmmem).

.EXAMPLE
    .\track_resources.ps1 -Solution hybrid
    # snapshot nhanh: máy có phù hợp chạy M2 ngay bây giờ không?

.EXAMPLE
    .\track_resources.ps1 -Solution hybrid -DurationSec 300 -IntervalSec 2 -Label "M2-smoke"
    # theo dõi 5 phút trong khi bạn chạy run_omnidocbench.py ở terminal khác

.EXAMPLE
    .\track_resources.ps1 -Solution hybrid -Command "uv run python scripts/run_omnidocbench.py --n 50" -Label "M2-50p"
    # chạy thẳng lệnh và đo trọn vòng đời của nó
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Solution,

    [string]$Command,

    [int]$DurationSec = 0,

    [int]$IntervalSec = 2,

    [string]$Label = "",

    [string]$Note = "",

    [string[]]$WatchProcess = @('python', 'pythonw', 'LM Studio', 'llama', 'vllm', 'docker', 'vmmem')
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Đường dẫn & xác thực giải pháp
# ---------------------------------------------------------------------------
$RnDRoot = Split-Path -Parent $PSScriptRoot          # tools/ -> RnD_pipeline/
$SolutionDir = Join-Path $RnDRoot $Solution
if (-not (Test-Path $SolutionDir -PathType Container)) {
    $known = (Get-ChildItem $RnDRoot -Directory | Where-Object { $_.Name -notin @('tools', 'eval') }).Name -join ', '
    throw "Khong thay giai phap '$Solution' tai $SolutionDir. Cac giai phap co: $known"
}
$OutDir = Join-Path $SolutionDir 'results\resources'
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

$Start = Get-Date
$Stamp = $Start.ToString('yyyyMMdd_HHmmss')
$SafeLabel = if ($Label) { ($Label -replace '[^\w\-]', '_') } else { 'run' }
$BaseName = "${Stamp}_${SafeLabel}"
$CsvPath = Join-Path $OutDir "$BaseName.samples.csv"
$ReportPath = Join-Path $OutDir "$BaseName.report.md"
$IndexPath = Join-Path $OutDir 'INDEX.md'

# ---------------------------------------------------------------------------
# Hàm lấy mẫu
# ---------------------------------------------------------------------------
function Get-RamSample {
    $os = Get-CimInstance Win32_OperatingSystem
    $totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 3)
    $freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 3)
    $usedGB = [math]::Round($totalGB - $freeGB, 3)
    [pscustomobject]@{
        TotalGB = $totalGB
        UsedGB  = $usedGB
        FreeGB  = $freeGB
        UsedPct = [math]::Round($usedGB / $totalGB * 100, 1)
    }
}

function Get-WslMemGB {
    $p = Get-Process -Name 'vmmem*' -ErrorAction SilentlyContinue
    if (-not $p) { return 0.0 }
    [math]::Round((($p | Measure-Object WorkingSet64 -Sum).Sum) / 1GB, 3)
}

function Get-CpuLoad {
    try {
        $avg = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
        if ($null -eq $avg) { return $null }
        [math]::Round([double]$avg, 1)
    } catch { return $null }
}

function Get-WatchMemGB {
    param([string[]]$Patterns)
    $total = 0.0
    foreach ($pat in $Patterns) {
        $procs = Get-Process -Name "$pat*" -ErrorAction SilentlyContinue
        if ($procs) { $total += (($procs | Measure-Object WorkingSet64 -Sum).Sum) / 1GB }
    }
    [math]::Round($total, 3)
}

$script:HasNvidiaSmi = $null -ne (Get-Command nvidia-smi -ErrorAction SilentlyContinue)

function ConvertTo-NullableDouble {
    param($v)
    if ($null -eq $v) { return $null }
    $s = ([string]$v).Trim()
    if ($s -eq '' -or $s -match '\[N/A\]' -or $s -eq '[Not Supported]') { return $null }
    $out = 0.0
    if ([double]::TryParse($s, [ref]$out)) { return [math]::Round($out, 2) }
    return $null
}

function Get-GpuSample {
    if (-not $script:HasNvidiaSmi) { return $null }
    try {
        $raw = & nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv,noheader,nounits
        if (-not $raw) { return $null }
        $f = ($raw | Select-Object -First 1) -split ','
        [pscustomobject]@{
            VramUsedMiB = ConvertTo-NullableDouble $f[0]
            VramFreeMiB = ConvertTo-NullableDouble $f[1]
            UtilGpuPct  = ConvertTo-NullableDouble $f[2]
            UtilMemPct  = ConvertTo-NullableDouble $f[3]
            TempC       = ConvertTo-NullableDouble $f[4]
            PowerW      = ConvertTo-NullableDouble $f[5]
        }
    } catch { return $null }
}

function Get-GpuStatic {
    if (-not $script:HasNvidiaSmi) { return $null }
    try {
        $raw = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
        $f = ($raw | Select-Object -First 1) -split ','
        [pscustomobject]@{
            Name         = $f[0].Trim()
            VramTotalMiB = ConvertTo-NullableDouble $f[1]
            Driver       = $f[2].Trim()
        }
    } catch { return $null }
}

function Get-GpuApps {
    if (-not $script:HasNvidiaSmi) { return @() }
    try {
        $raw = & nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader,nounits
        if (-not $raw) { return @() }
        $raw | ForEach-Object {
            $f = $_ -split ','
            [pscustomobject]@{
                Pid     = $f[0].Trim()
                VramMiB = ConvertTo-NullableDouble $f[1]
                Name    = ($f[2..($f.Count - 1)] -join ',').Trim()
            }
        }
    } catch { return @() }
}

function Test-LmStudioUp {
    $c = Get-NetTCPConnection -LocalPort 1234 -State Listen -ErrorAction SilentlyContinue
    [bool]$c
}

function Get-TopProcs {
    param([int]$N = 6)
    Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First $N |
        ForEach-Object { [pscustomobject]@{ Name = $_.Name; MemGB = [math]::Round($_.WorkingSet64 / 1GB, 2); Id = $_.Id } }
}

# ---------------------------------------------------------------------------
# Thông tin máy (tĩnh)
# ---------------------------------------------------------------------------
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$gpuStatic = Get-GpuStatic
$Machine = [pscustomobject]@{
    Host       = $env:COMPUTERNAME
    OS         = "$($os.Caption) $($os.Version)"
    Cores      = $cs.NumberOfLogicalProcessors
    RamTotalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    Gpu        = if ($gpuStatic) { "$($gpuStatic.Name) ($([math]::Round($gpuStatic.VramTotalMiB/1024,1)) GB, driver $($gpuStatic.Driver))" } else { 'khong phat hien NVIDIA GPU' }
}
$VramTotalMiB = if ($gpuStatic) { $gpuStatic.VramTotalMiB } else { $null }

# ---------------------------------------------------------------------------
# Vòng lấy mẫu
# ---------------------------------------------------------------------------
$samples = New-Object System.Collections.Generic.List[object]
$peakTopProcs = $null
$peakRamUsed = -1

function Add-Sample {
    $ram = Get-RamSample
    $gpu = Get-GpuSample
    $t = [math]::Round(((Get-Date) - $Start).TotalSeconds, 1)
    $row = [pscustomobject]@{
        ElapsedSec  = $t
        Time        = (Get-Date).ToString('HH:mm:ss')
        RamUsedGB   = $ram.UsedGB
        RamUsedPct  = $ram.UsedPct
        RamFreeGB   = $ram.FreeGB
        WslMemGB    = Get-WslMemGB
        WatchMemGB  = Get-WatchMemGB -Patterns $WatchProcess
        CpuPct      = Get-CpuLoad
        VramUsedMiB = if ($gpu) { $gpu.VramUsedMiB } else { $null }
        VramFreeMiB = if ($gpu) { $gpu.VramFreeMiB } else { $null }
        GpuUtilPct  = if ($gpu) { $gpu.UtilGpuPct } else { $null }
        GpuTempC    = if ($gpu) { $gpu.TempC } else { $null }
        GpuPowerW   = if ($gpu) { $gpu.PowerW } else { $null }
        LmStudioUp  = Test-LmStudioUp
    }
    $samples.Add($row)
    if ($ram.UsedGB -gt $script:peakRamUsed) {
        $script:peakRamUsed = $ram.UsedGB
        $script:peakTopProcs = Get-TopProcs -N 6
    }
    return $row
}

$mode = 'snapshot'
$exitCode = $null
$wallSec = $null

if ($Command) { $mode = 'wrap' }
elseif ($DurationSec -gt 0) { $mode = 'monitor' }

Write-Host "[track] Solution=$Solution  Mode=$mode  Interval=${IntervalSec}s" -ForegroundColor Cyan
Write-Host "[track] Bao cao se ghi vao: $OutDir" -ForegroundColor Cyan

switch ($mode) {
    'snapshot' {
        $r = Add-Sample
        Write-Host ("[track] RAM {0}% | WSL {1}GB | VRAM {2}/{3} MiB | LMStudio={4}" -f `
            $r.RamUsedPct, $r.WslMemGB, $r.VramUsedMiB, $VramTotalMiB, $r.LmStudioUp)
    }
    'monitor' {
        $end = $Start.AddSeconds($DurationSec)
        Write-Host "[track] Theo doi $DurationSec giay... (Ctrl+C de dung som)" -ForegroundColor Yellow
        while ((Get-Date) -lt $end) {
            $r = Add-Sample
            Write-Host ("  t+{0,5}s  RAM {1,5}%  VRAM {2,6} MiB  GPU {3,3}%  CPU {4,3}%" -f `
                $r.ElapsedSec, $r.RamUsedPct, $r.VramUsedMiB, $r.GpuUtilPct, $r.CpuPct)
            Start-Sleep -Seconds $IntervalSec
        }
        Add-Sample | Out-Null
    }
    'wrap' {
        Write-Host "[track] Chay lenh: $Command" -ForegroundColor Yellow
        $proc = Start-Process -FilePath 'powershell.exe' `
            -ArgumentList @('-NoProfile', '-NoLogo', '-Command', $Command) `
            -PassThru -NoNewWindow
        while (-not $proc.HasExited) {
            $r = Add-Sample
            Write-Host ("  t+{0,5}s  RAM {1,5}%  VRAM {2,6} MiB  GPU {3,3}%  CPU {4,3}%" -f `
                $r.ElapsedSec, $r.RamUsedPct, $r.VramUsedMiB, $r.GpuUtilPct, $r.CpuPct)
            Start-Sleep -Seconds $IntervalSec
        }
        Add-Sample | Out-Null
        $exitCode = $proc.ExitCode
        $wallSec = [math]::Round(($proc.ExitTime - $proc.StartTime).TotalSeconds, 1)
        Write-Host "[track] Lenh ket thuc. ExitCode=$exitCode  Wall=${wallSec}s" -ForegroundColor Cyan
    }
}

# ---------------------------------------------------------------------------
# Thống kê
# ---------------------------------------------------------------------------
function Stat {
    param([string]$Field)
    $vals = $samples | ForEach-Object { $_.$Field } | Where-Object { $null -ne $_ }
    if (-not $vals) { return $null }
    $m = $vals | Measure-Object -Minimum -Maximum -Average
    [pscustomobject]@{
        Min = [math]::Round($m.Minimum, 1)
        Avg = [math]::Round($m.Average, 1)
        Max = [math]::Round($m.Maximum, 1)
    }
}

$sRamPct = Stat 'RamUsedPct'
$sRamGB = Stat 'RamUsedGB'
$sWsl = Stat 'WslMemGB'
$sWatch = Stat 'WatchMemGB'
$sCpu = Stat 'CpuPct'
$sVram = Stat 'VramUsedMiB'
$sVramFree = Stat 'VramFreeMiB'
$sGpuUtil = Stat 'GpuUtilPct'
$sTemp = Stat 'GpuTempC'
$sPower = Stat 'GpuPowerW'

# ---------------------------------------------------------------------------
# Đánh giá (verdict)
# ---------------------------------------------------------------------------
$findings = New-Object System.Collections.Generic.List[string]
$level = 'OK'      # OK | WARN | RISK

$peakRamPct = if ($sRamPct) { $sRamPct.Max } else { 0 }
if ($peakRamPct -ge 90) { $level = 'RISK'; $findings.Add("RAM dinh ${peakRamPct}% (>=90%) -> nguy co cham/he thong page rat manh.") }
elseif ($peakRamPct -ge 75) { if ($level -eq 'OK') { $level = 'WARN' }; $findings.Add("RAM dinh ${peakRamPct}% (>=75%) -> can theo doi, dong bot ung dung nen.") }

if ($null -ne $VramTotalMiB -and $sVramFree) {
    $minFree = $sVramFree.Min
    $minFreeGB = [math]::Round($minFree / 1024, 2)
    if ($minFree -lt 1024) { $level = 'RISK'; $findings.Add("VRAM trong toi thieu chi ${minFreeGB}GB (<1GB) -> nguy co OOM / model offload xuong CPU (cham nhieu lan).") }
    elseif ($minFree -lt 2048) { if ($level -ne 'RISK') { $level = 'WARN' }; $findings.Add("VRAM trong toi thieu ${minFreeGB}GB (<2GB) -> sat tran, tranh load them model GPU thu 2.") }
}

$lastLm = ($samples | Select-Object -Last 1).LmStudioUp
if ($Solution -eq 'hybrid' -and -not $lastLm) {
    if ($level -eq 'OK') { $level = 'WARN' }
    $findings.Add("LM Studio KHONG listen port 1234 -> Tier B (Qwen3-VL) chua san sang. Bat Local Server + load model truoc khi chay M2.")
}
if (-not $script:HasNvidiaSmi) { $findings.Add("Khong tim thay nvidia-smi -> khong do duoc VRAM (chi co so RAM/CPU).") }
if ($findings.Count -eq 0) { $findings.Add("Khong phat hien rui ro. May du tai nguyen de chay.") }

$verdictText = switch ($level) {
    'OK'   { 'PHU HOP — may du tai nguyen de chay giai phap nay.' }
    'WARN' { 'CANH BAO — chay duoc nhung sat nguong, theo doi ky.' }
    'RISK' { 'NGUY CO — co the OOM/cham nghiem trong, xu ly truoc khi chay.' }
}

$gpuApps = Get-GpuApps

# ---------------------------------------------------------------------------
# Ghi CSV
# ---------------------------------------------------------------------------
$samples | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8

# ---------------------------------------------------------------------------
# Dựng báo cáo Markdown
# ---------------------------------------------------------------------------
function MdRow3 { param($name, $stat, $unit = '') if ($stat) { "| $name | $($stat.Min)$unit | $($stat.Avg)$unit | $($stat.Max)$unit |" } else { "| $name | - | - | - |" } }

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Bao cao tai nguyen — $Solution")
$lines.Add('')
$lines.Add("> **Verdict**: **$level** — $verdictText")
$lines.Add('')
$lines.Add('## Metadata')
$lines.Add('')
$lines.Add('| Truong | Gia tri |')
$lines.Add('|---|---|')
$lines.Add("| Solution | $Solution |")
$lines.Add("| Mode | $mode |")
$lines.Add("| Label | $Label |")
$lines.Add("| Bat dau | $($Start.ToString('yyyy-MM-dd HH:mm:ss')) |")
$lines.Add("| So mau | $($samples.Count) (moi ${IntervalSec}s) |")
if ($mode -eq 'wrap') {
    $lines.Add("| Lenh | ``$Command`` |")
    $lines.Add("| ExitCode | $exitCode |")
    $lines.Add("| Wall time | ${wallSec}s |")
}
if ($Note) { $lines.Add("| Ghi chu | $Note |") }
$lines.Add('')
$lines.Add('## May')
$lines.Add('')
$lines.Add('| Truong | Gia tri |')
$lines.Add('|---|---|')
$lines.Add("| Host | $($Machine.Host) |")
$lines.Add("| OS | $($Machine.OS) |")
$lines.Add("| Logical cores | $($Machine.Cores) |")
$lines.Add("| RAM tong | $($Machine.RamTotalGB) GB |")
$lines.Add("| GPU | $($Machine.Gpu) |")
$lines.Add('')
$lines.Add('## Tong hop tai nguyen (min / avg / peak)')
$lines.Add('')
$lines.Add('| Chi so | Min | Avg | Peak |')
$lines.Add('|---|---|---|---|')
$lines.Add((MdRow3 'RAM da dung (%)' $sRamPct '%'))
$lines.Add((MdRow3 'RAM da dung (GB)' $sRamGB ' GB'))
$lines.Add((MdRow3 'WSL/vmmem (GB)' $sWsl ' GB'))
$lines.Add((MdRow3 'Watch-process RAM (GB)' $sWatch ' GB'))
$lines.Add((MdRow3 'CPU load (%)' $sCpu '%'))
$lines.Add((MdRow3 'VRAM da dung (MiB)' $sVram ' MiB'))
$lines.Add((MdRow3 'VRAM trong (MiB)' $sVramFree ' MiB'))
$lines.Add((MdRow3 'GPU util (%)' $sGpuUtil '%'))
$lines.Add((MdRow3 'GPU temp (C)' $sTemp ' C'))
$lines.Add((MdRow3 'GPU power (W)' $sPower ' W'))
$lines.Add('')
$lines.Add("LM Studio (port 1234) cuoi mau: **$lastLm**")
$lines.Add('')
$lines.Add('## Danh gia & khuyen nghi')
$lines.Add('')
foreach ($f in $findings) { $lines.Add("- $f") }
$lines.Add('')
if ($peakTopProcs) {
    $lines.Add('## Tien trinh ngon RAM nhat (luc dinh RAM)')
    $lines.Add('')
    $lines.Add('| Process | Mem (GB) | PID |')
    $lines.Add('|---|---|---|')
    foreach ($p in $peakTopProcs) { $lines.Add("| $($p.Name) | $($p.MemGB) | $($p.Id) |") }
    $lines.Add('')
}
$gpuAppsWithMem = @($gpuApps | Where-Object { $_.VramMiB -and $_.VramMiB -gt 0 } | Sort-Object VramMiB -Descending)
$lines.Add('## Tien trinh dang giu VRAM (nvidia-smi)')
$lines.Add('')
if ($gpuAppsWithMem.Count -gt 0) {
    $lines.Add('| PID | VRAM (MiB) | Process |')
    $lines.Add('|---|---|---|')
    foreach ($a in $gpuAppsWithMem) { $lines.Add("| $($a.Pid) | $($a.VramMiB) | $($a.Name) |") }
} else {
    $lines.Add('> nvidia-smi khong bao duoc VRAM per-process tren GPU consumer/WDDM (Windows).')
    $lines.Add('> Tong VRAM da dung xem o bang tren; tren may nay phan lon do **LM Studio** (model dang load) giu.')
}
$lines.Add('')
$lines.Add("> Du lieu mau day du: ``$(Split-Path -Leaf $CsvPath)`` (cung thu muc).")

Set-Content -Path $ReportPath -Value ($lines -join "`r`n") -Encoding UTF8

# ---------------------------------------------------------------------------
# Cập nhật INDEX
# ---------------------------------------------------------------------------
if (-not (Test-Path $IndexPath)) {
    Set-Content -Path $IndexPath -Value "# Resource tracking — $Solution`r`n`r`n| Thoi gian | Mode | Label | Verdict | Peak RAM% | Peak VRAM MiB | Bao cao |`r`n|---|---|---|---|---|---|---|" -Encoding UTF8
}
$peakVram = if ($sVram) { $sVram.Max } else { '-' }
$indexRow = "| $($Start.ToString('yyyy-MM-dd HH:mm')) | $mode | $Label | $level | $peakRamPct | $peakVram | [$([System.IO.Path]::GetFileName($ReportPath))]($([System.IO.Path]::GetFileName($ReportPath))) |"
Add-Content -Path $IndexPath -Value $indexRow -Encoding UTF8

# ---------------------------------------------------------------------------
# In tóm tắt
# ---------------------------------------------------------------------------
Write-Host ''
Write-Host "===== VERDICT: $level =====" -ForegroundColor $(if ($level -eq 'OK') { 'Green' } elseif ($level -eq 'WARN') { 'Yellow' } else { 'Red' })
Write-Host $verdictText
foreach ($f in $findings) { Write-Host "  - $f" }
Write-Host ''
Write-Host "Bao cao : $ReportPath" -ForegroundColor Green
Write-Host "CSV     : $CsvPath" -ForegroundColor Green
Write-Host "Index   : $IndexPath" -ForegroundColor Green

