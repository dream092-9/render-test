#!/usr/bin/env python3
"""
Render에 배포되는 Python 엔드포인트: GET / → "hello, world"
로컬 실행: python hello.py [--serve]
배포 후 호출: RENDER_SERVICE_ID, RENDER_SERVICE_URL 설정 후 python hello.py --deploy-and-call
"""
import argparse
import json
import os
import subprocess
import sys
import time

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    return "hello, world"


@app.route("/health")
def health():
    return {"status": "ok"}, 200


def get_service_url_from_cli(service_id: str) -> str | None:
    """Render CLI로 서비스 목록을 조회해 service_id에 해당하는 URL 반환."""
    try:
        out = subprocess.run(
            ["render", "services", "-o", "json", "--confirm"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "CI": "true"},
        )
        if out.returncode != 0:
            return None
        data = json.loads(out.stdout)
        # CLI 응답: 리스트 또는 { services: [...] } 등 구조에 맞게 탐색
        services = data if isinstance(data, list) else data.get("services", data)
        if not isinstance(services, list):
            services = [services]
        for svc in services:
            sid = svc.get("id") or svc.get("serviceId")
            if sid == service_id:
                # serviceDetails 등에 URL이 있을 수 있음
                url = (
                    svc.get("serviceDetails", {}).get("url")
                    or svc.get("url")
                    or svc.get("service", {}).get("serviceDetails", {}).get("url")
                )
                if url:
                    return url
                name = svc.get("name") or svc.get("service", {}).get("name")
                if name:
                    slug = name.lower().replace(" ", "-")
                    return f"https://{slug}.onrender.com"
        return None
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def main_serve():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def main_deploy_and_call():
    service_id = os.environ.get("RENDER_SERVICE_ID")
    service_url = os.environ.get("RENDER_SERVICE_URL")

    if not service_id and not service_url:
        print(
            "RENDER_SERVICE_ID 또는 RENDER_SERVICE_URL 환경 변수를 설정하세요.",
            file=sys.stderr,
        )
        print(
            "예: RENDER_SERVICE_ID=srv-xxx python hello.py --deploy-and-call",
            file=sys.stderr,
        )
        sys.exit(1)

    if service_url:
        url = service_url.rstrip("/")
    else:
        print("RENDER_SERVICE_URL이 없어 CLI로 서비스 URL 조회 중...")
        url = get_service_url_from_cli(service_id)
        if not url:
            print(
                "서비스 URL을 찾을 수 없습니다. RENDER_SERVICE_URL을 직접 설정하세요.",
                file=sys.stderr,
            )
            sys.exit(1)
        url = url.rstrip("/")

    if service_id:
        print("Render 배포 트리거 중...")
        try:
            subprocess.run(
                [
                    "render", "deploys", "create", service_id,
                    "--wait", "-o", "json", "--confirm",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
                env={**os.environ, "CI": "true"},
            )
        except subprocess.CalledProcessError as e:
            print(f"배포 실패: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print("render CLI를 찾을 수 없습니다. 설치 후 PATH에 추가하세요.", file=sys.stderr)
            sys.exit(1)
        print("배포 완료.")

    # 호출
    try:
        import urllib.request
        with urllib.request.urlopen(f"{url}/", timeout=30) as resp:
            body = resp.read().decode()
            print("응답:", body)
            if "hello" in body.lower() and "world" in body.lower():
                print("OK: hello, world 수신")
            else:
                print("경고: 예상과 다른 응답입니다.", file=sys.stderr)
    except Exception as e:
        print(f"엔드포인트 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hello World 엔드포인트 (로컬 서버 또는 배포 후 호출)")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="로컬에서 Flask 서버 실행 (기본: 서버 실행)",
    )
    parser.add_argument(
        "--deploy-and-call",
        action="store_true",
        help="Render CLI로 배포 트리거 후 엔드포인트 호출",
    )
    args = parser.parse_args()

    if args.deploy_and_call:
        main_deploy_and_call()
    else:
        main_serve()
