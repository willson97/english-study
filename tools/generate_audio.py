"""
빨모쌤 영어학습 — TTS 오디오 자동생성 스크립트
=====================================================
용도: txt 파일을 파싱해서 영어 문장을 mp3로 변환
출력: audio/ppalmmo_epXX_NNN.mp3

파일명 규칙: ppalmmo_ep{에피소드번호:02d}_{에피소드내순번:03d}.mp3
  예) ppalmmo_ep01_001.mp3, ppalmmo_ep06_013.mp3

사용법:
  python generate_audio.py                  # ID 없는 문장 자동처리 (txt 업데이트 + 오디오 생성)
  python generate_audio.py --force          # 이미 있는 파일도 재생성
  python generate_audio.py --dry-run        # 처리 목록만 출력 (실제 생성 안 함)
  python generate_audio.py --txt <경로>     # txt 파일 경로 지정

워크플로우:
  1. txt 파일에 새 문장 추가 (ID 태그 없이 그냥 작성)
  2. python generate_audio.py 실행
  3. 스크립트가 알아서:
     - ID 없는 문장 탐지
     - 에피소드별 다음 번호 자동 할당 (예: ep06_014)
     - txt 파일에 [epXX_NNN] 태그 삽입
     - 오디오 파일 생성

필요 패키지:
  pip install google-cloud-texttospeech

인증 설정:
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
"""

import os
import re
import sys
import time
import argparse

# ── 설정 ──────────────────────────────────────────────────────
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
TXT_FILE     = "ppalmmo_live_for_now.txt"
AUDIO_DIR    = "audio"
AUDIO_PREFIX = "ppalmmo_"
TTS_LANGUAGE = "en-US"
TTS_VOICE    = "en-US-Journey-D"   # Journey-D: 남성 / Journey-F: 여성
TTS_SPEED    = 0.9
# ─────────────────────────────────────────────────────────────

HAS_KOREAN = lambda t: any('\uAC00' <= c <= '\uD7A3' for c in t)
ID_PATTERN = re.compile(r'\[ep(\d{2})_(\d{3})\]')


def parse_txt(txt_path):
    """
    txt 파일을 파싱하여 문장 목록 반환.
    각 항목: {line_idx, ep_num, ep_pos, english, audio_id, has_id}
    - line_idx: 영어 줄의 인덱스 (0-based)
    - audio_id: 기존 ID가 있으면 "ep01_001" 형태, 없으면 None
    """
    with open(txt_path, encoding='utf-8') as f:
        lines = f.readlines()

    sentences = []
    current_ep = 0
    ep_counter = {}  # ep_num → 현재까지 발견된 최대 pos

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        ep_match = re.match(r'Episode:\s*(\d+)\.', stripped)
        if ep_match:
            current_ep = int(ep_match.group(1))
            i += 1
            continue

        if (current_ep > 0 and stripped and
            not stripped.startswith('*') and
            not stripped.startswith('{') and
            not stripped.startswith('}') and
            not stripped.startswith('출처') and
            not stripped.startswith('id:') and
            not stripped.startswith('주제:') and
            HAS_KOREAN(stripped)):

            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if (next_stripped and
                    not next_stripped.startswith('*') and
                    next_stripped not in ('{', '}') and
                    not next_stripped.startswith('Episode:') and
                    not next_stripped.startswith('주제:') and
                    not HAS_KOREAN(next_stripped)):

                    id_match = ID_PATTERN.search(next_stripped)
                    if id_match:
                        ep_n = int(id_match.group(1))
                        ep_p = int(id_match.group(2))
                        audio_id = f'ep{ep_n:02d}_{ep_p:03d}'
                        ep_counter[ep_n] = max(ep_counter.get(ep_n, 0), ep_p)
                    else:
                        audio_id = None
                        ep_counter.setdefault(current_ep, 0)

                    english_clean = ID_PATTERN.sub('', next_stripped).strip()

                    sentences.append({
                        'line_idx':  i + 1,
                        'ep_num':    current_ep,
                        'audio_id':  audio_id,
                        'english':   english_clean,
                        'raw_line':  lines[i + 1],
                    })
                    i += 2
                    continue
        i += 1

    return sentences, lines, ep_counter


def assign_ids(sentences, ep_counter):
    """ID 없는 문장에 다음 순번 할당. sentences 직접 수정."""
    # 에피소드별 현재 최대값 기반으로 순번 결정
    next_pos = {ep: cnt for ep, cnt in ep_counter.items()}

    for s in sentences:
        if s['audio_id'] is None:
            ep = s['ep_num']
            next_pos[ep] = next_pos.get(ep, 0) + 1
            s['audio_id'] = f'ep{ep:02d}_{next_pos[ep]:03d}'
            s['new_id'] = True
        else:
            s['new_id'] = False


def update_txt(txt_path, sentences, lines):
    """ID가 새로 할당된 문장들의 줄에 태그 삽입 후 저장."""
    new_lines = list(lines)
    for s in sentences:
        if s['new_id']:
            old = new_lines[s['line_idx']]
            tag = f'[{s["audio_id"]}]'
            newline_char = '\n' if old.endswith('\n') else ''
            new_lines[s['line_idx']] = old.rstrip('\n').rstrip() + ' ' + tag + newline_char
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def get_audio_path(audio_id):
    return os.path.join(AUDIO_DIR, f'{AUDIO_PREFIX}{audio_id}.mp3')


def generate_mp3(client, text, out_path):
    from google.cloud import texttospeech
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=TTS_LANGUAGE,
        name=TTS_VOICE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=TTS_SPEED,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice_params, audio_config=audio_config,
    )
    with open(out_path, 'wb') as f:
        f.write(response.audio_content)


def main():
    parser = argparse.ArgumentParser(description='빨모쌤 TTS 생성기')
    parser.add_argument('--force',   action='store_true', help='이미 있는 파일도 재생성')
    parser.add_argument('--dry-run', action='store_true', help='처리 목록만 출력')
    parser.add_argument('--txt',     default=TXT_FILE,   help=f'txt 파일 경로 (기본값: {TXT_FILE})')
    args = parser.parse_args()

    if GOOGLE_CREDENTIALS_JSON:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_CREDENTIALS_JSON

    if not os.path.exists(args.txt):
        print(f'❌ 파일을 찾을 수 없습니다: {args.txt}')
        sys.exit(1)

    sentences, lines, ep_counter = parse_txt(args.txt)
    print(f'✅ 파싱 완료: {len(sentences)}개 문장')

    assign_ids(sentences, ep_counter)

    new_count = sum(1 for s in sentences if s['new_id'])
    if new_count:
        print(f'🆕 새 ID 할당: {new_count}개')

    os.makedirs(AUDIO_DIR, exist_ok=True)

    targets = []
    for s in sentences:
        out_path = get_audio_path(s['audio_id'])
        if args.force or not os.path.exists(out_path):
            targets.append(s)

    if not targets:
        print('✅ 생성할 파일이 없습니다. (모두 이미 존재)')
        if new_count:
            update_txt(args.txt, sentences, lines)
            print(f'📝 txt 파일에 {new_count}개 ID 태그 추가 완료')
        return

    print(f'🎙️  생성 대상: {len(targets)}개 파일')
    print(f'   목소리: {TTS_VOICE} / 속도: {TTS_SPEED}')
    print()

    if args.dry_run:
        for s in targets:
            label = '🆕' if s['new_id'] else '  '
            print(f'  {label} [{s["audio_id"]}] {get_audio_path(s["audio_id"])}')
            print(f'       "{s["english"][:60]}"')
        print(f'\n총 {len(targets)}개 (--dry-run: 실제 생성 안 함)')
        return

    # txt 업데이트 (오디오 생성 전에 먼저)
    if new_count:
        update_txt(args.txt, sentences, lines)
        print(f'📝 txt 파일에 {new_count}개 ID 태그 추가 완료\n')

    # Google Cloud TTS 클라이언트
    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
    except ImportError:
        print('❌ google-cloud-texttospeech 패키지가 없습니다.')
        print('   pip install google-cloud-texttospeech 를 실행하세요.')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Google Cloud 인증 실패: {e}')
        sys.exit(1)

    success, failed = 0, []
    for s in targets:
        out_path = get_audio_path(s['audio_id'])
        label = '🆕 ' if s['new_id'] else '   '
        try:
            print(f'  {label}[{s["audio_id"]}] 생성 중... "{s["english"][:50]}"', end='', flush=True)
            generate_mp3(client, s['english'], out_path)
            size_kb = os.path.getsize(out_path) // 1024
            print(f' → {size_kb}KB ✅')
            success += 1
            time.sleep(0.5)
        except Exception as e:
            print(f' ❌ 오류: {e}')
            failed.append((s['audio_id'], str(e)))

    print()
    print(f'🎉 완료: {success}개 성공', end='')
    if failed:
        print(f' / {len(failed)}개 실패')
        for aid, err in failed:
            print(f'   [{aid}] {err}')
    else:
        print()
    print(f'\n📁 저장 위치: {os.path.abspath(AUDIO_DIR)}/')


if __name__ == '__main__':
    main()
