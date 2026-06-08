# Chạy đánh giá OmniDocBench bằng 1 lệnh trên Windows.
#   .\run_eval.ps1                       # dùng config mặc định end2end_local.yaml
#   .\run_eval.ps1 end2end_demo_local    # chạy smoke-test trên demo
#   .\run_eval.ps1 -Config configs\end2end_local.yaml
#
# Tự động: bật PYTHONUTF8=1 (bắt buộc — code OmniDocBench đọc JSON không khai báo
# encoding nên crash trên Windows nếu thiếu) và dùng python của conda env 'omnidocbench'.
param(
    [string]$Config = "configs/end2end_local.yaml"
)

$EvalRoot = $PSScriptRoot
$RepoDir  = Join-Path $EvalRoot "OmniDocBench_eval"
$EnvPy    = "$env:USERPROFILE\.conda\envs\omnidocbench\python.exe"

if (-not (Test-Path $EnvPy)) {
    Write-Error "Không thấy python của env 'omnidocbench' tại $EnvPy. Tạo env: conda create -n omnidocbench python=3.10 -y; conda run -n omnidocbench pip install -e .\OmniDocBench_eval"
    exit 1
}

# Cho phép truyền tên config ngắn gọn (không cần 'configs/' và '.yaml')
if ($Config -notmatch '[\\/]' -and $Config -notmatch '\.ya?ml$') {
    $Config = "configs/$Config.yaml"
}

$env:PYTHONUTF8 = "1"
Push-Location $RepoDir
try {
    Write-Host "==> Chạy: $EnvPy pdf_validation.py --config $Config" -ForegroundColor Cyan
    & $EnvPy pdf_validation.py --config $Config
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "`n[X] pdf_validation.py thoát với exit code $code" -ForegroundColor Red
        Pop-Location
        exit $code
    }
    Write-Host "`n==> Kết quả trong: $RepoDir\result\" -ForegroundColor Green
    # Copy metric tổng hợp ra eval/results cho dễ xem
    $resultsOut = Join-Path $EvalRoot "results"
    Copy-Item "$RepoDir\result\*_metric_result.json" $resultsOut -Force -ErrorAction SilentlyContinue
    Copy-Item "$RepoDir\result\*_run_summary.json"   $resultsOut -Force -ErrorAction SilentlyContinue
} finally {
    Pop-Location
}
