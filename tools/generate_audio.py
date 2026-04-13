"""
빨모쌤 영어학습 — TTS 오디오 자동생성 스크립트
=====================================================
용도: txt 파일을 파싱해서 영어 문장을 mp3로 변환
출력: audio/ppalmmo_live_NNN.mp3

사용법:
  python generate_audio.py                      # 전체 생성 (없는 파일만)
  python generate_audio.py --force              # 전체 재생성
  python generate_audio.py --from 102           # 102번부터만 생성
  python generate_audio.py --dry-run            # 생성 목록만 출력 (실제 생성 안 함)

필요 패키지:
  pip install google-cloud-texttospeech

API 키 설정 (둘 중 하나):
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
  또는 스크립트 내 GOOGLE_CREDENTIALS_JSON 변수에 서비스 계정 JSON 경로 직접 입력
"""

import os
import re
import sys
import time
import argparse

# ── 설정 ──────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")  # 서비스 계정 JSON 경로
TXT_FILE       = "ppalmmo_live_for_now.txt"             # 파싱할 txt 파일 경로
AUDIO_DIR      = "audio"                                # 출력 폴더
AUDIO_PREFIX   = "ppalmmo_live_"                        # 파일명 접두사
TTS_LANGUAGE   = "en-US"                                # 언어 코드
TTS_VOICE      = "en-US-Journey-D"                      # 보이스 이름 (Journey-D: 남성, Journey-F: 여성)
TTS_SPEED      = 0.9                                    # 재생 속도 (0.25 ~ 4.0), 학습용은 0.85~0.95 권장
# ─────────────────────────────────────────────────────────────


def parse_sentences(txt_path):
    """txt 파일에서 (순번, 한국어, 영어) 리스트 반환"""
    with open(txt_path, encoding='utf-8') as f:
        lines = f.read().split('\n')

    sentences = []
    i = 0
    in_dialogue = False

    while i < len(lines):
        line = lines[i].strip()

        if line == '{':
            in_dialogue = True; i += 1; continue
        if line == '}':
            in_dialogue = False; i += 1; continue
        if (line.startswith('Episode:') or line.startswith('주제:') or
                line.startswith('출처') or line.startswith('id:') or
                line.startswith('*') or not line):
            i += 1; continue

        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if (next_line and not next_line.startswith('*') and
                    next_line not in ('{', '}') and
                    not next_line.startswith('Episode:') and
                    not next_line.startswith('주제:')):
                has_korean      = any('\uAC00' <= c <= '\uD7A3' for c in line)
                has_korean_next = any('\uAC00' <= c <= '\uD7A3' for c in next_line)
                if has_korean and not has_korean_next:
                    sentences.append({
                        'idx':     len(sentences) + 1,
                        'korean':  line,
                        'english': next_line,
                    })
                    i += 2
                    continue
        i += 1

    return sentences


def generate_mp3(client, text, out_path, speed=0.9, voice="en-US-Journey-D", language="en-US"):
    """Google Cloud TTS API로 mp3 생성"""
    from google.cloud import texttospeech

    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=language,
        name=voice,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speed,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    with open(out_path, "wb") as f:
        f.write(response.audio_content)


def main():
    parser = argparse.ArgumentParser(description='빨모쌤 TTS 생성기 (Google Cloud)')
    parser.add_argument('--force',   action='store_true', help='이미 있는 파일도 재생성')
    parser.add_argument('--from',       dest='from_idx',   type=int, default=1,    help='시작 순번 (기본값: 1)')
    parser.add_argument('--file-start', dest='file_start', type=int, default=None, help='파일 번호 시작값 (기본값: --from 값과 동일). 기존 파일과 번호 충돌 시 사용')
    parser.add_argument('--dry-run', action='store_true', help='생성 목록만 출력')
    parser.add_argument('--txt',     default=TXT_FILE, help=f'txt 파일 경로 (기본값: {TXT_FILE})')
    args = parser.parse_args()

    # 인증 확인
    creds = GOOGLE_CREDENTIALS_JSON
    if creds:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds

    # txt 파일 파싱
    if not os.path.exists(args.txt):
        print(f"❌ 파일을 찾을 수 없습니다: {args.txt}")
        sys.exit(1)

    sentences = parse_sentences(args.txt)
    print(f"✅ 파싱 완료: {len(sentences)}개 문장 발견")

    # 출력 폴더 생성
    os.makedirs(AUDIO_DIR, exist_ok=True)

    # 생성 대상 필터링
    file_start = args.file_start if args.file_start is not None else args.from_idx
    targets = []
    for s in sentences:
        if s['idx'] < args.from_idx:
            continue
        file_idx = file_start + (s['idx'] - args.from_idx)
        out_path = os.path.join(AUDIO_DIR, f"{AUDIO_PREFIX}{file_idx:03d}.mp3")
        if not args.force and os.path.exists(out_path):
            continue  # 이미 존재 → 스킵
        targets.append((s, out_path))

    if not targets:
        print("✅ 생성할 파일이 없습니다. (모두 이미 존재)")
        return

    print(f"🎙️  생성 대상: {len(targets)}개 파일")
    print(f"   목소리: {TTS_VOICE} / 속도: {TTS_SPEED} / 언어: {TTS_LANGUAGE}")
    print()

    if args.dry_run:
        for s, out_path in targets:
            print(f"  [{s['idx']:03d}] {out_path}  ← \"{s['english'][:50]}\"")
        print(f"\n총 {len(targets)}개 파일이 생성될 예정입니다. (--dry-run: 실제 생성 안 함)")
        return

    # Google Cloud TTS 클라이언트 초기화
    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
    except ImportError:
        print("❌ google-cloud-texttospeech 패키지가 없습니다.")
        print("   pip install google-cloud-texttospeech 를 실행하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Google Cloud 인증 실패: {e}")
        print("   GOOGLE_APPLICATION_CREDENTIALS 환경변수에 서비스 계정 JSON 경로를 설정하세요.")
        sys.exit(1)

    # 생성 실행
    success = 0
    failed  = []

    for s, out_path in targets:
        try:
            print(f"  [{s['idx']:03d}] 생성 중... \"{s['english'][:55]}\"", end='', flush=True)
            generate_mp3(client, s['english'], out_path, speed=TTS_SPEED, voice=TTS_VOICE, language=TTS_LANGUAGE)
            size_kb = os.path.getsize(out_path) // 1024
            print(f" → {size_kb}KB ✅")
            success += 1
            time.sleep(0.5)  # API 레이트 리밋 방지
        except Exception as e:
            print(f" ❌ 오류: {e}")
            failed.append((s['idx'], str(e)))

    print()
    print(f"🎉 완료: {success}개 성공", end='')
    if failed:
        print(f" / {len(failed)}개 실패")
        for idx, err in failed:
            print(f"   [{idx:03d}] {err}")
    else:
        print()

    print(f"\n📁 저장 위치: {os.path.abspath(AUDIO_DIR)}/")
    print("   GitHub에 audio/ 폴더째로 업로드하면 학습 앱에서 바로 재생됩니다.")


if __name__ == '__main__':
    main()
