# fix_numpy.ps1 — repairs a broken (MINGW-compiled) numpy on Windows.
# Symptom it fixes: server crashes silently with no traceback during scraping,
# and logs show "Numpy built with MINGW-W64 ... CRASHES ARE TO BE EXPECTED".
#
# Run from the job-search-app directory inside your venv:
#   .\fix_numpy.ps1

Write-Host "Removing broken numpy/pandas..." -ForegroundColor Yellow
pip uninstall numpy pandas -y

Write-Host "Reinstalling from prebuilt wheels only (no source builds)..." -ForegroundColor Green
# --only-binary refuses to compile from source; if no wheel exists it errors
# instead of building a broken one.
pip install numpy==2.2.6 pandas==2.2.3 --only-binary=:all:

Write-Host "`nVerifying numpy works..." -ForegroundColor Cyan
python -c "import numpy as np; import numpy.core.getlimits; print('numpy', np.__version__, 'OK'); print(np.finfo(np.float64))"

Write-Host "`nIf you saw 'OK' with no MINGW warning, numpy is fixed." -ForegroundColor Green
