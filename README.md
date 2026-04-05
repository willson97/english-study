# 빨모쌤 English Lab — GitHub 저장소 구조

## 📁 폴더 구조

```
english-study/                  ← GitHub 저장소 루트
│
├── index.html                  ← 학습 앱 (메인 파일)
│
├── audio/                      ← mp3 파일 폴더
│   ├── ppalmmo_live_001.mp3
│   ├── ppalmmo_live_002.mp3
│   ├── ...
│   └── ppalmmo_live_324.mp3
│
├── generate_audio.py           ← TTS 자동생성 스크립트 (로컬 전용)
└── README.md                   ← 이 파일
```

## 🚀 GitHub Pages 배포 주소
```
https://[사용자명].github.io/english-study
```

## 🎵 mp3 파일 업로드 방법

### 방법 A — GitHub 웹에서 직접 (소량)
1. 저장소 → `audio/` 폴더 클릭
2. `Add file` → `Upload files`
3. mp3 파일들 드래그&드롭 → `Commit changes`

### 방법 B — GitHub Desktop 앱 (대량, 권장)
1. https://desktop.github.com 에서 GitHub Desktop 설치
2. `Clone repository` → `english-study` 선택
3. 로컬 폴더에 `audio/` 폴더 생성 후 mp3 파일 복사
4. GitHub Desktop에서 `Commit to main` → `Push origin`

### 방법 C — Claude Code (자동화)
```bash
cd english-study
git add audio/
git commit -m "Add audio files"
git push
```

## 🆕 새 에피소드 추가 워크플로우

1. **txt 파일에 새 에피소드 추가**
2. **Claude 채팅에서**: txt 파일 첨부 → "앱 업데이트해줘"
3. **TTS 생성**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   python generate_audio.py --from 325    # 325번부터 새로 생성
   ```
4. **GitHub에 업로드**:
   - `index.html` 교체
   - `audio/` 에 새 mp3 추가
5. **1~2분 후** GitHub Pages 자동 반영 ✅

## 🎙️ TTS 목소리 옵션 (generate_audio.py 설정)

| 목소리 | 특징 |
|--------|------|
| alloy  | 중성적, 깔끔 (기본값) |
| echo   | 남성적, 차분 |
| fable  | 영국식, 표현력 있음 |
| nova   | 여성적, 밝고 자연스러움 |
| shimmer| 여성적, 부드러움 |

속도: `TTS_SPEED = 0.9` (학습용 권장: 0.85~0.95)
