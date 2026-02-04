# 배포 가이드 (Render + GitHub)

이 문서는 이 프로젝트가 Render와 GitHub를 통해 어떻게 배포되는지 정리한 것이며, 다음 배포 시 참고용입니다.

---

## 1. 개요

- **목적**: Python Flask 웹 서비스(`hello.py`)를 Render에서 실행하고, GitHub 저장소와 연결해 push 시 자동 배포.
- **저장소**: `https://github.com/dream092-9/render-test` (기본 브랜치: `master`)
- **원격**: `origin` → `https://github.com/dream092-9/render-test.git`
- **서비스 URL 예시**: `https://hello-world-fo9c.onrender.com` (서비스별로 접미사 `-fo9c` 등은 Render가 부여)

---

## 2. Render 배포 구조

### 2.1 정의 파일: `render.yaml`

- **위치**: 프로젝트 루트의 `render.yaml`
- **역할**: Render Blueprint(IaC). 서비스 타입·빌드·시작 명령을 코드로 정의.

| 항목 | 값 |
|------|-----|
| 서비스 타입 | `web` |
| 서비스 이름 | `hello-world` |
| 런타임 | `python` |
| 플랜 | `free` |
| 빌드 | `pip install -r requirements.txt` |
| 시작 | `gunicorn hello:app --bind 0.0.0.0:$PORT` |

- **앱 진입점**: `hello:app` → `hello.py`의 Flask `app` 객체.

### 2.2 배포 방식

- **방법 1 (Blueprint)**  
  - Render 대시보드에서 **New > Blueprint** 선택 후 이 GitHub 저장소 연결.  
  - `render.yaml`이 있는 브랜치(예: `master`)를 연결.  
  - Blueprint 적용 시 `render.yaml`에 정의된 서비스가 생성·업데이트되고, 해당 브랜치 push 시 자동 배포될 수 있음.

- **방법 2 (웹 서비스 수동 연결)**  
  - **New > Web Service**로 저장소 연결 후, 빌드/시작 명령을 `render.yaml`과 동일하게 설정.

- **실제 배포 이력**: GitHub Deployments API 기준 `master - hello-world` 환경, `ref: master`, `task: deploy`로 배포된 기록이 있음 (자동 배포 또는 수동 Deploy).

---

## 3. GitHub 쪽 확인 (gh CLI)

```bash
# 저장소 정보
gh repo view --json name,url,defaultBranchRef

# 최근 배포 이력
gh api repos/dream092-9/render-test/deployments --jq ".[0] | {id, environment, ref, task, created_at}"

# 원격 브랜치 확인
git remote -v
git branch -a
```

- 이 프로젝트에는 `.github/workflows`가 없음 → 배포 트리거는 **Render의 “Git 연결 + 자동 배포”** 또는 **Render 대시보드/CLI에서의 수동 Deploy**로 동작하는 구조로 보면 됨.

---

## 4. Render 쪽 확인 (Render CLI)

```bash
# CLI 버전
render --version

# 로그인 (브라우저에서 인증)
render login

# 서비스 목록 (로그인 후)
render services list
# 또는 JSON 출력
render services list -o json
```

- 서비스 목록·로그·재배포 등은 **Render 대시보드** 또는 **로그인된 Render CLI**로 확인.

---

## 5. 다음 배포를 위한 절차

### 5.1 코드 변경 후 배포 (일반적인 경우)

1. **로컬에서 수정 후 커밋**
   ```bash
   git add .
   git commit -m "메시지"
   ```

2. **GitHub에 push**
   ```bash
   git push origin master
   ```

3. **Render 동작**
   - 저장소가 “Auto-Deploy”로 연결되어 있으면, `master`(또는 연결된 브랜치)에 push 시 자동으로 새 배포가 시작됨.
   - 대시보드에서 **Services > hello-world > Deploys**에서 진행 상황 확인.

### 5.2 render.yaml 변경 시 (Blueprint 사용 시)

- `render.yaml`을 수정한 뒤 위와 같이 커밋·push.
- Render Blueprint를 쓰는 경우, 대시보드에서 **Blueprint** 화면에 들어가 변경 사항을 검토한 뒤 **Apply** 하면 새 설정이 반영되고 필요한 서비스가 재배포됨.

### 5.3 서비스 URL 확인

- **대시보드**: Render Dashboard > **Services** > **hello-world** > 상단/설정에 표시되는 URL.
- **로컬 호출 스크립트**: `호출_helloworld.py`, `호출_extract_productdata.py`, `호출_extract_productdata_multi.py` 등에서 사용하는 기본 URL이 `https://hello-world-fo9c.onrender.com` 으로 하드코딩되어 있음.  
  - Render에서 URL이 바뀌면(예: 서비스 재생성) 이 주소를 각 스크립트 또는 환경 변수에서 맞춰 수정해야 함.

---

## 6. 로컬/클라이언트 환경

- **환경 변수 (선택)**
  - `RENDER_SERVICE_URL`: 배포된 서비스 URL (예: `https://hello-world-fo9c.onrender.com`)
  - `RENDER_SERVICE_ID`: Render 서비스 ID (CLI/API로 URL 조회 시 사용 가능)
- **의존성**: `requirements.txt` (flask, gunicorn, requests, aiohttp 등). Render 빌드 시 여기 기준으로 설치됨.

---

## 7. Cloudflare Workers 배포 (네이버 상품 데이터 스크래퍼)

### 7.1 개요

- **목적**: 네이버 쇼핑 상품 데이터를 추출하는 서버리스 함수를 Cloudflare Workers에 배포
- **Worker 이름**: `naver-product-data`
- **Worker URL**: `https://naver-product-data.dreamad0929.workers.dev`
- **배포 날짜**: 2026-02-04

### 7.2 구성 파일

| 파일 | 용도 |
|------|------|
| `z_workers_endpoint.js` | Workers용 JavaScript 코드 (메인 엔드포인트) |
| `wrangler.toml` | Wrangler 설정 파일 (Worker 이름, 호환성 날짜 등) |
| `package.json` | NPM 패키지 설정 |
| `z_workers_endpoint.py` | 로컬에서 Workers를 호출하는 Python 스크립트 |
| `deploy_worker.bat` | Windows용 배포 스크립트 |
| `DEPLOY_GUIDE.md` | 상세 배포 가이드 |

### 7.3 주요 기능

1. **중복 제거 및 복원**: 같은 nvmid가 여러 번 요청되면 중복 제거 후 한 번만 요청하고 결과를 복원
2. **순차 처리**: Workers 하위 요청 제한(요청당 50개)으로 인해 순차적으로 처리
3. **CORS 지원**: 모든 출처에서 요청 허용
4. **HTML 파싱**: 네이버 쇼핑 페이지에서 상품 정보 추출

### 7.4 배포 방법

#### 방법 1: 명령줄에서 직접 배포
```bash
cd D:\render_test
npx wrangler deploy
```

#### 방법 2: 배포 스크립트 사용 (Windows)
```bash
deploy_worker.bat
```

### 7.5 Workers 사용 방법

#### Python 스크립트로 호출
```bash
# 기본 사용
python z_workers_endpoint.py https://naver-product-data.dreamad0929.workers.dev

# 커스텀 경로 및 동시 처리 수 지정
python z_workers_endpoint.py https://naver-product-data.dreamad0929.workers.dev D:\nvmids.txt D:\scripts D:\output 20
```

#### cURL로 직접 호출
```bash
curl -X POST https://naver-product-data.dreamad0929.workers.dev/extract_productdata_batch \
  -H "Content-Type: application/json" \
  -d '{
    "nvmids": ["10267318504"],
    "cookies": "your_cookie_string",
    "headers": {}
  }'
```

### 7.6 API 엔드포인트

- **POST** `/extract_productdata_batch`
  - 요청 본문:
    ```json
    {
      "nvmids": ["10267318504", "89175572471"],
      "cookies": "cookie_string",
      "headers": {},
      "concurrency": 20
    }
    ```
  - 응답:
    ```json
    {
      "success": true,
      "total": 2,
      "success_count": 2,
      "fail_count": 0,
      "original_unique_nvmids": 2,
      "duplicates_removed": 0,
      "results": [...]
    }
    ```

### 7.7 결과 파일

- `zz_workers.json`: Workers 호출 결과가 저장되는 파일

### 7.8 제한 사항 및 주의사항

- **하위 요청 제한**: Workers 무료 플랜은 요청당 50개의 하위 요청만 허용
- **순차 처리**: 제한으로 인해 병렬 처리가 아닌 순차 처리로 구현
- **타임아웃**: Workers 최대 실행 시간은 CPU 시간으로 30초 (무료 플랜)
- **일일 요청 제한**: 무료 플랜 일일 100,000개 요청

### 7.9 재배포 절차

1. `z_workers_endpoint.js` 수정
2. `npx wrangler deploy` 실행
3. 배포 완료 메시지 확인
4. Python 스크립트로 테스트

---

## 8. 요약 체크리스트 (다음 배포 시)

- [ ] 변경 사항 커밋 후 `git push origin master` (또는 연결된 브랜치)
- [ ] Render 대시보드에서 Deploy 완료 여부 확인
- [ ] 필요 시 서비스 URL 변경 시 호출 스크립트/환경 변수 업데이트
- [ ] `render.yaml` 수정 시 Blueprint 사용 중이면 대시보드에서 Apply
- [ ] Workers 재배포 시 `npx wrangler deploy` 실행
- [ ] Workers 업데이트 시 `z_workers_endpoint.js` 수정 후 배포
