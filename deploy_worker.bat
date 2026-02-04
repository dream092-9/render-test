@echo off
REM Cloudflare Workers 배포 스크립트 (Windows)

echo ==================================================
echo Cloudflare Workers 배포 시작
echo ==================================================
echo.

REM 현재 디렉토리 이동
cd /d D:\render_test

echo [1/4] 필수 파일 확인...
if not exist "z_workers_endpoint.js" (
    echo ❌ 오류: z_workers_endpoint.js 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

if not exist "wrangler.toml" (
    echo ❌ 오류: wrangler.toml 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo ✅ 필수 파일 확인 완료
echo.

echo [2/4] Wrangler 로그인 상태 확인...
wrangler whoami >nul 2>&1
if errorlevel 1 (
    echo ⚠️  로그인되어 있지 않습니다. 로그인을 시작합니다...
    wrangler login
) else (
    echo ✅ 이미 로그인되어 있습니다.
)
echo.

echo [3/4] Worker 배포 중...
npx wrangler deploy

if errorlevel 1 (
    echo.
    echo ==================================================
    echo ❌ 배포 실패
    echo ==================================================
    echo.
    echo 오류 메시지를 확인하고 문제를 해결한 후 다시 시도하세요.
    echo.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo ✅ 배포 성공!
echo ==================================================
echo.
echo Workers URL: https://naver-product-data.YOUR_SUBDOMAIN.workers.dev
echo.
echo 다음 명령어로 테스트하세요:
echo python z_workers_endpoint.py https://naver-product-data.YOUR_SUBDOMAIN.workers.dev
echo.

echo [4/4] 배포 정보 확인...
npx wrangler deployments list

echo.
pause
