

## 1. 사용한 라이브러리 

### 1-1. Python 표준 라이브러리

| 라이브러리 | 주요 용도 | 대표 사용처 |
| --- | --- | --- |
| `os` | 파일 경로 합성, 파일/폴더 존재 확인, 폴더 생성, 파일 목록 조회 | `create_records_dir`, `list_audio_files`, 파일 경로 조립 전반 |
| `sys` | 비정상 종료(`sys.exit`), 명령행 인자(`sys.argv`) 처리 | import 실패 시 종료, `--cli` 옵션 처리 |
| `csv` | CSV 읽기·쓰기 | `save_stt_csv`, `read_csv_entries`, `search_keyword_in_csv` |
| `json` | 북마크(즐겨찾기) JSON 직렬화/역직렬화 | `load_bookmarks`, `save_bookmarks` |
| `wave` | WAV 파일 헤더 조작 및 PCM 데이터 읽기/쓰기 | `save_wav_file`, `split_wav_to_chunks`, `record_audio_with_event` |
| `datetime` | 파일명 타임스탬프 생성, 날짜 문자열 파싱 | `generate_filename`, `list_recordings_by_date`, `filter_wav_files_by_date` |
| `threading` | 백그라운드 녹음/STT 워커, 종료 신호용 Event | `record_audio`, `_start_recording`, `_run_stt_in_thread` |
| `tkinter` (+ `ttk`, `filedialog`, `messagebox`) | GUI 구현 (창, 위젯, 다이얼로그, 파일 선택, 메시지 박스) | `JavisGUI` 클래스 전체 |

### 1-2. 외부 라이브러리 

| 라이브러리 | 주요 용도 | 허용 근거 |
| --- | --- | --- |
| `pyaudio` | 시스템 마이크 장치 탐색, 오디오 스트림 열기, PCM 청크 읽기 | 미션 제약: *시스템의 마이크를 인식하고 음성을 녹음하는 부분은 외부 라이브러리를 사용하는 것이 가능하다* |
| `speech_recognition` (`sr`) | WAV 청크에 대한 음성 인식 (Google STT 호출) | 미션 11 제약: *STT는 별도의 외부 라이브러리를 사용하는 것이 가능하다* |

---

## 2. import 블록 코드 

```python
import os
import sys
import csv
import json
import wave
import datetime
import threading

try:
    import pyaudio
except ImportError:
    print('오류: pyaudio 라이브러리가 필요합니다.')
    print('설치 명령어: pip install pyaudio')
    sys.exit(1)

try:
    import speech_recognition as sr
except ImportError:
    print('오류: SpeechRecognition 라이브러리가 필요합니다.')
    print('설치 명령어: pip install SpeechRecognition')
    sys.exit(1)

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False
```

**왜 이렇게 했나?**
- 외부 라이브러리는 `try / except ImportError`로 감싸 미설치 환경에서도 친절한 안내 메시지를 보여주고 종료. 그냥 import만 하면 `ModuleNotFoundError` 스택트레이스만 떠서 사용자가 원인을 파악하기 어렵기 때문.
- `tkinter`는 표준 라이브러리이지만 macOS 미니멀 설치본·일부 Linux 배포판에서 누락될 수 있어, 가용 여부를 `TK_AVAILABLE` 플래그로 보관해 진입점에서 GUI ↔ CLI 폴백을 결정

---

## 3. 카테고리별 함수 상세 설명

### 3-1. 공통 유틸리티

#### `create_records_dir()` — `os` 모듈

```python
def create_records_dir():
    """records 폴더가 없으면 생성한다."""
    try:
        if not os.path.exists(RECORDS_DIR):
            os.makedirs(RECORDS_DIR)
            print(f'[폴더 생성] {RECORDS_DIR} 폴더를 생성했습니다.')
    except PermissionError:
        print(f'오류: {RECORDS_DIR} 폴더를 생성할 권한이 없습니다.')
        sys.exit(1)
```

- `os.path.exists(path)`: 폴더가 이미 있는지 확인. 매번 새로 만들지 않도록 함.
- `os.makedirs(path)`: 다중 계층 디렉터리를 한 번에 생성. (이번엔 단층이지만 일관성 차원에서 `makedirs` 사용)
- `PermissionError`만 따로 잡아 사용자에게 친절히 안내. 다른 종류의 예외는 의도적으로 잡지 않아 디버깅에 유리.

#### `seconds_to_time_str(total_seconds)`

```python
def seconds_to_time_str(total_seconds):
    """초(float)를 HH:MM:SS 형식의 문자열로 변환한다."""
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
```

- 외부 모듈 사용 없이 산술 연산만으로 변환. `datetime.timedelta`를 쓸 수도 있지만`0:01:30` 형식을 기본으로 내놓아 자릿수 패딩이 일관되지 않아서 직접 구현했음.
- `f'{n:02d}'` 포맷 스펙으로 2자리 0-패딩.

#### `generate_filename()` — `datetime` 모듈

```python
def generate_filename():
    """현재 날짜와 시간을 기반으로 WAV 파일 이름을 생성한다."""
    now = datetime.datetime.now()
    return now.strftime('%Y%m%d-%H%M%S') + '.wav'
```

- `datetime.datetime.now()`: 로컬 시스템 시각 객체를 반환.
- `strftime('%Y%m%d-%H%M%S')`: `20260528-143022` 같은 정렬 가능한 문자열. 미션 10에서 정의한 파일명 규칙을 그대로 따름. 후속 `filter_wav_files_by_date`에서 이 포맷을 역으로 파싱하기 때문에 일관성이 중요.

---

### 3-2. 녹음 기능 (외부 라이브러리 `pyaudio` 사용)

#### `get_microphone_info(audio)` — `pyaudio`

```python
def get_microphone_info(audio):
    device_count = audio.get_device_count()
    print('\n[마이크 탐색] 시스템에서 사용 가능한 입력 장치:')

    has_input = False
    for i in range(device_count):
        device_info = audio.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:
            print(f'  장치 [{i}] : {device_info["name"]}')
            has_input = True
    ...
    default_info = audio.get_default_input_device_info()
    return int(default_info['index'])
```

- `audio.get_device_count()` / `get_device_info_by_index(i)`: 시스템에 연결된 모든 오디오 장치를 순회.
- `maxInputChannels > 0` 조건으로 **입력 장치(마이크)**만 필터링. 스피커 등 출력만 가능한 장치 제외.
- `get_default_input_device_info()`: OS의 기본 입력 장치를 자동 선택. 사용자가 별도 설정 없이도 동작하도록.
- **왜 `pyaudio`?** 파이썬 표준 라이브러리에는 마이크 캡처 기능이 없음. `pyaudio`는 크로스 플랫폼이고 미션 제약상 명시적으로 허용됨.

#### `save_wav_file(file_path, audio, frames)` — `wave` + `pyaudio`

```python
def save_wav_file(file_path, audio, frames):
    with wave.open(file_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
```

- `wave.open(path, 'wb')`: 표준 라이브러리만으로 WAV 파일 헤더를 정확히 작성할 수 있음. 외부 라이브러리 불필요.
- `audio.get_sample_size(FORMAT)`: `pyaudio.paInt16` 같은 포맷 상수에 대응되는 바이트 수를 계산. WAV 헤더의 `sampwidth` 필드에 들어감.
- `frames`는 `stream.read()`로 얻은 PCM 청크 리스트이고, `b''.join(frames)`으로 한 번에 직렬화해 디스크 I/O를 최소화.

#### `record_audio_with_event(stop_event, status_callback=None)` — GUI/스레드용 

```python
def record_audio_with_event(stop_event, status_callback=None):
    create_records_dir()
    audio = pyaudio.PyAudio()
    stream = None
    frames = []

    try:
        default_info = audio.get_default_input_device_info()
        input_device = int(default_info['index'])
        ...
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=CHUNK,
        )
        ...
        while not stop_event.is_set():
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            ...
        ...
    finally:
        # 어떤 상황에서도 오디오 자원을 정리한다.
        if stream is not None:
            try: stream.stop_stream()
            except Exception: pass
            try: stream.close()
            except Exception: pass
        try: audio.terminate()
        except Exception: pass
```

- `threading.Event`를 받아 GUI 스레드(메인)와 녹음 워커 사이 종료 신호 전달. `input()`을 쓰는 CLI용 `record_audio()`와 달리 GUI 메인 루프를 막지 않음.
- `stream.read(CHUNK, exception_on_overflow=False)`: 약 23ms 단위로 PCM 청크를 가져옴. `exception_on_overflow=False`로 두면 버퍼 오버플로우가 발생해도 예외 대신 그냥 진행해 녹음이 끊기지 않음.
- `try / finally` 패턴: 어떤 경로(정상/예외/조기 종료)로 빠져나가도 `stream.close()` + `audio.terminate()`가 반드시 실행되도록 보장. PyAudio 자원을 누수시키면 다음 녹음 시 장치를 못 열 수 있음.
- `status_callback`: 메인 스레드에 경과 시간을 알릴 콜백. GUI 상태바에 "녹음 중... ● (00:00:05)"를 갱신하기 위해 사용.

#### `record_audio()` — CLI용 (Enter 키로 정지)

```python
def record_audio():
    ...
    is_recording = [True]
    def stop_on_enter():
        input()
        is_recording[0] = False
    stop_thread = threading.Thread(target=stop_on_enter, daemon=True)
    stop_thread.start()
    ...
    while is_recording[0]:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
```

- `threading.Thread(target=..., daemon=True)`: `input()`이 메인 루프를 막지 않도록 별도 스레드에서 대기. `daemon=True`로 메인 종료 시 자동 정리.
- 상태 공유를 위해 `[True]` 형태의 1원소 리스트를 사용 — 람다 클로저에서 수정 가능한 가변 객체로 다루기 위한 흔한 패턴.

---

### 3-3. 날짜 검색

#### `filter_wav_files_by_date(file_names, start, end)` — `datetime` 파싱

```python
def filter_wav_files_by_date(file_names, start_date_str, end_date_str):
    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y%m%d')
        end_date = datetime.datetime.strptime(end_date_str, '%Y%m%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        return [], '날짜 형식이 올바르지 않습니다 (YYYYMMDD).'
    ...
    for file_name in file_names:
        name_without_ext = file_name.replace('.wav', '')
        try:
            file_dt = datetime.datetime.strptime(
                name_without_ext, '%Y%m%d-%H%M%S'
            )
        except ValueError:
            continue
        if start_date <= file_dt <= end_date:
            matched.append(file_name)
    return matched, ''
```

- `datetime.strptime(s, fmt)`: 문자열을 `datetime` 객체로 변환. 잘못된 형식은 `ValueError`로 잡아 사용자 친화 메시지로 변환.
- `end_date.replace(hour=23, minute=59, second=59)`: 종료일을 그 날의 끝까지 포함하도록 보정. 그러지 않으면 "20260528 ~ 20260528"이 0시 0분으로 끝나 그날 녹음이 모두 빠짐.
- 파일명 자체를 시간 정보로 사용 — `generate_filename()`이 보장하는 포맷이라 따로 메타데이터 파일을 둘 필요가 없음. 가벼운 설계.

---

### 3-4. STT 변환 (외부 라이브러리 `speech_recognition` 사용)

#### `split_wav_to_chunks(wav_path)` — `wave` + `sr.AudioData`

```python
def split_wav_to_chunks(wav_path):
    chunks = []
    with wave.open(wav_path, 'rb') as wf:
        frame_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        n_frames = wf.getnframes()
        frames_per_chunk = frame_rate * STT_CHUNK_SECONDS

        offset = 0
        while offset < n_frames:
            wf.setpos(offset)
            chunk_frame_count = min(frames_per_chunk, n_frames - offset)
            raw_data = wf.readframes(chunk_frame_count)
            audio_data = sr.AudioData(raw_data, frame_rate, sample_width)
            start_seconds = offset / frame_rate
            chunks.append((start_seconds, audio_data))
            offset += frames_per_chunk
    return chunks
```

- `wave`는 표준 라이브러리만으로 WAV 메타데이터(framerate, sampwidth, nframes)를 정확히 얻을 수 있음.
- `wf.setpos(offset)` + `wf.readframes(n)`: WAV 내부에서 임의 위치 점프 후 일정 길이만큼 PCM을 읽음 → **30초 단위 청크**로 자르는 데 사용. 한 번에 너무 긴 오디오를 STT API에 보내면 인식 정확도 저하/타임아웃이 생김.
- `sr.AudioData(raw_data, frame_rate, sample_width)`: `speech_recognition`이 인식기에 넘기는 표준 컨테이너. 직접 `recognize_*` 함수에 전달 가능.
- 반환값에 `start_seconds`를 함께 담아 CSV의 "시간" 컬럼을 채울 수 있게 함.

#### `transcribe_audio_file(wav_path)` — Google STT 호출

```python
def transcribe_audio_file(wav_path):
    recognizer = sr.Recognizer()
    chunks = split_wav_to_chunks(wav_path)
    results = []
    ...
    for start_seconds, audio_data in chunks:
        time_str = seconds_to_time_str(start_seconds)
        try:
            text = recognizer.recognize_google(audio_data, language='ko-KR')
            results.append((time_str, text))
        except sr.UnknownValueError:
            # 해당 구간에서 음성을 인식하지 못한 경우 건너뜀
            ...
        except sr.RequestError as e:
            print(f'오류: STT 서비스에 접근할 수 없습니다 → {e}')
            break
    return results
```

- `recognizer.recognize_google(audio_data, language='ko-KR')`: Google Web Speech API에 청크를 전송하고 한국어 인식 결과를 받음. 별도 API 키 없이 호출 가능한 무료 엔드포인트라 미션용으로 적합.
- 두 가지 예외를 분리해서 처리:
  - `sr.UnknownValueError`: 그 구간에 음성이 없거나 너무 작아서 인식 불가 → 다음 청크로 계속.
  - `sr.RequestError`: 네트워크/서비스 자체에 문제 → 더 진행해도 의미가 없으니 `break`.

#### `save_stt_csv(wav_file_name, stt_results)` — `csv` 모듈

```python
def save_stt_csv(wav_file_name, stt_results):
    ...
    csv_file_name = wav_file_name.replace('.wav', '.csv')
    csv_path = os.path.join(RECORDS_DIR, csv_file_name)

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['시간', '인식된 텍스트'])
        writer.writerows(stt_results)
```

- `csv.writer` + `writerows`: 헤더 한 줄 쓰고 모든 결과를 한 번에 기록. 직접 `,` 조합해서 쓰면 텍스트 안에 쉼표/따옴표가 있을 때 깨지지만 `csv` 모듈은 자동으로 이스케이프 처리해 줌.
- `encoding='utf-8-sig'`: Excel에서 한글이 깨지지 않도록 BOM 포함. 한송희 박사가 Excel로도 열어볼 수 있게 함.
- `newline=''`: Windows에서 `\r\n`이 두 번 들어가는 문제 방지(PEP 8 / Python 공식 권장).

---

### 3-5. 키워드 검색 (CLI 버전)

#### `search_keyword_in_csv(keyword)` — `csv` + `os`

```python
def search_keyword_in_csv(keyword):
    ...
    csv_files = sorted([
        f for f in os.listdir(RECORDS_DIR) if f.endswith('.csv')
    ])
    ...
    for csv_file_name in csv_files:
        csv_path = os.path.join(RECORDS_DIR, csv_file_name)
        ...
        with open(csv_path, 'r', encoding='utf-8-sig') as csv_file:
            reader = csv.reader(csv_file)
            next(reader, None)  # 헤더 행 건너뜀
            for row in reader:
                if len(row) < 2:
                    continue
                time_str, text = row[0], row[1]
                if keyword.lower() in text.lower():
                    found_in_file.append((time_str, text))
```

- `os.listdir(RECORDS_DIR)`: 폴더 내 파일명을 가져온 뒤 `.csv` 확장자만 필터링.
- `csv.reader` + `next(reader, None)`: 첫 행(헤더 "시간/인식된 텍스트")은 검색 대상에서 제외하기 위해 한 번 소비.
- `keyword.lower() in text.lower()`: 대소문자 구분 없이 부분 일치 검색.

---

### 3-6. 북마크 (즐겨찾기) — `json` 영속 저장

#### `load_bookmarks()`, `save_bookmarks(bookmarks)` — `json`

```python
def load_bookmarks():
    if not os.path.exists(BOOKMARKS_FILE):
        return {}
    try:
        with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as bm_file:
            data = json.load(bm_file)
            if isinstance(data, dict):
                return data
            return {}
    except (json.JSONDecodeError, OSError) as e:
        print(f'오류: 북마크 파일을 읽을 수 없습니다 → {e}')
        return {}


def save_bookmarks(bookmarks):
    try:
        with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as bm_file:
            json.dump(bookmarks, bm_file, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f'오류: 북마크 저장에 실패했습니다 → {e}')
```

- 북마크 구조는 `{ 'CSV파일명': ['HH:MM:SS', ...] }` 형태. 단순한 dict라서 추가 ORM 같은 게 필요 없고 `json` 한 줄로 직렬화 가능.
- `ensure_ascii=False`: 한글이 `\uXXXX` 이스케이프 형태로 저장되지 않고 그대로 저장돼 사람이 직접 읽고 디버깅 가능.
- `indent=2`: 사람이 열어보기 좋은 들여쓰기. 어차피 작은 파일이므로 용량 손해도 없음.
- `isinstance(data, dict)` 가드: 누가 실수로 JSON 파일을 다른 타입(리스트 등)으로 덮어써도 안전하게 빈 dict 반환.

#### `toggle_bookmark(bookmarks, csv_file, time_str)` — 순수 dict 조작

```python
def toggle_bookmark(bookmarks, csv_file, time_str):
    times = bookmarks.get(csv_file, [])
    if time_str in times:
        times.remove(time_str)
        if times:
            bookmarks[csv_file] = times
        else:
            bookmarks.pop(csv_file, None)
        return False

    times.append(time_str)
    bookmarks[csv_file] = times
    return True
```

- 표준 라이브러리만으로 (라이브러리 호출 없이) 토글 로직 구현.
- 빈 리스트가 되면 키 자체를 제거 → JSON 파일이 깔끔하게 유지됨.

---

### 3-7. 통계 / 내보내기

#### `collect_statistics(bookmarks)` — `os` + `csv` + 산술

```python
def collect_statistics(bookmarks):
    wav_files = list_audio_files()
    csv_files = list_csv_files()
    wav_set = {name.replace('.wav', '') for name in wav_files}
    csv_set = {name.replace('.csv', '') for name in csv_files}

    transcribed = len(wav_set & csv_set)
    not_transcribed = len(wav_set - csv_set)
    ...
    return {
        'wav_count': len(wav_files),
        'csv_count': len(csv_files),
        'transcribed': transcribed,
        'not_transcribed': not_transcribed,
        'utterances': total_utterances,
        'chars': total_chars,
        'bookmarks': sum(len(t) for t in bookmarks.values()),
    }
```

- **set 연산**으로 "변환된 / 안 된" 파일을 한 줄에 계산: `wav_set & csv_set`은 교집합(=변환 완료), `wav_set - csv_set`은 차집합(=미변환).
- 표준 라이브러리 외 어떤 통계 패키지도 안 씀 — 단순 누적과 set만으로 충분.

#### `export_results_to_txt(file_path, results, keyword)` — 파일 I/O

```python
def export_results_to_txt(file_path, results, keyword=None):
    with open(file_path, 'w', encoding='utf-8') as out_file:
        out_file.write('JAVIS - 화성 기지 음성 기록 검색 결과\n')
        out_file.write('=' * 50 + '\n')
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        out_file.write(f'내보낸 시각: {now_str}\n')
        ...
        current_file = None
        for csv_file, time_str, text in results:
            if csv_file != current_file:
                out_file.write(f'\n[파일] {csv_file}\n')
                out_file.write('-' * 50 + '\n')
                current_file = csv_file
            out_file.write(f'  [{time_str}]  {text}\n')
```

- 외부 템플릿 엔진 없이 일반 텍스트로 직접 작성. CSV로 내보내도 되지만 사람이 읽기 좋은 보고서 형태가 더 자연스러워 `.txt`를 선택.
- 파일별로 헤더를 한 번씩 출력하면서 그룹핑.

---

### 3-8. GUI (`tkinter` / `ttk`)

전체 GUI는 `JavisGUI` 클래스 하나로 모여 있으며, 핵심 위젯 구성은 표준 `tkinter` + `tkinter.ttk` 만 사용합니다.

#### 헤더 + 툴바 빌드 — `ttk.Frame`, `ttk.Label`, `ttk.Button`

```python
def _build_header(self):
    header = ttk.Frame(self.root, style='Header.TFrame')
    header.pack(side=tk.TOP, fill=tk.X)

    inner = ttk.Frame(
        header, style='Header.TFrame', padding=(20, 14, 20, 14)
    )
    inner.pack(fill=tk.X)

    ttk.Label(inner, text='🛰  JAVIS', style='HeaderTitle.TLabel').pack(side=tk.LEFT)
    ttk.Label(
        inner,
        text='   화성 기지 음성 기록 시스템 · 음성에서 문자로',
        style='HeaderSubtitle.TLabel',
    ).pack(side=tk.LEFT, anchor='s', pady=(0, 3))
```

- `ttk.Style().configure('Header.TFrame', ...)`로 미리 정의한 스타일을 위젯에 적용 → CSS-like 분리.
- `pack(side=tk.LEFT, fill=tk.X)`: 가로로 가득 차고 좌측 정렬되는 단순 레이아웃.

#### 검색 입력칸 — `tk.Entry` (한글 IME 호환)

```python
self.search_entry = tk.Entry(
    search_bar,
    textvariable=self.search_var,
    font=('TkDefaultFont', 12),
    width=36,
    relief='flat',
    highlightthickness=1,
    highlightbackground=self.COLOR_BORDER,
    highlightcolor=self.COLOR_PRIMARY,
    bg='white',
    fg=self.COLOR_FG,
    insertbackground=self.COLOR_PRIMARY,
)
self.search_entry.bind('<Return>', lambda e: self.do_search())
self.search_entry.bind(
    '<Button-1>',
    lambda e: self.search_entry.focus_set(),
)
```

- **`ttk.Entry` 대신 `tk.Entry`를 쓰는 이유**: macOS 환경에서 `ttk.Entry`가 한국어 IME 입력을 가끔 삼키는 알려진 이슈가 있어, 가장 호환성 좋은 클래식 `tk.Entry`로 교체.
- `bind('<Return>', ...)`: Enter 키로 즉시 검색 실행.
- `bind('<Button-1>', ...)`: 클릭 즉시 포커스를 가져와 한글 입력이 보장되도록.

#### Treeview (검색 결과) — `ttk.Treeview` + 태그 컬러

```python
self.tree = ttk.Treeview(
    tree_container, columns=columns, show='headings', height=20
)
self.tree.heading('star', text='★')
self.tree.heading('time', text='시간')
self.tree.heading('text', text='인식된 텍스트')
self.tree.heading('file', text='파일')
...
self.tree.tag_configure('odd', background=self.COLOR_ALT_ROW)
self.tree.tag_configure('even', background=self.COLOR_PANEL)
self.tree.tag_configure('hit', background=self.COLOR_HIGHLIGHT)
self.tree.tag_configure(
    'bookmarked',
    foreground=self.COLOR_BOOKMARK,
    font=('TkDefaultFont', 11, 'bold'),
)

self.tree.bind('<Double-1>', self._on_tree_activate)
self.tree.bind('<Return>', self._on_tree_activate)
self.tree.bind('<space>', self._on_tree_activate)
```

- `ttk.Treeview`: 표 형식 데이터를 보여줄 때 표준 라이브러리에서 제공하는 가장 적절한 위젯. `show='headings'`로 트리 펼치기 화살표를 숨기고 순수 표로 사용.
- `tag_configure` + `tag`를 이용해 행 단위 스타일링 (홀짝 줄, 매칭 행, 북마크 행). HTML/CSS의 클래스 개념과 비슷.
- 더블 클릭/Enter/Space 모두 같은 핸들러에 바인딩 → 사용자 친화적인 다중 입력 경로.

#### 녹음 스레드 시작 / 종료 — `threading.Event`

```python
def _start_recording(self):
    self.record_stop_event = threading.Event()
    self.is_recording = True
    self.record_btn.config(text='● 녹음 중지', style='Recording.TButton')

    def worker():
        try:
            ok, file_path, message = record_audio_with_event(
                self.record_stop_event,
                status_callback=lambda elapsed: self.root.after(
                    0,
                    lambda e=elapsed: self.set_status(
                        f'녹음 중... ● ({seconds_to_time_str(e)})'
                    ),
                ),
            )
        except Exception as exc:
            ok, file_path, message = (
                False, None, f'예기치 않은 오류: {exc}'
            )
        self.root.after(
            0,
            lambda: self._after_recording_done(ok, file_path, message),
        )

    threading.Thread(target=worker, daemon=True).start()
```

- `threading.Event`: 스레드 간 안전한 신호 전달 객체. 메인 스레드에서 `set()` 호출, 워커 스레드에서 `is_set()`으로 폴링.
- **워커를 `try/except`로 감싸는 이유**: 예외가 발생해도 메인 스레드에서 후처리(`_after_recording_done`)가 반드시 실행돼 녹음 버튼이 다시 "녹음 시작"으로 복구되도록.
- `self.root.after(0, callback)`: 워커 스레드에서 GUI 위젯을 직접 조작하면 tkinter가 깨지므로, 메인 이벤트 루프에 콜백 예약을 통해 안전하게 화면 갱신.
- `daemon=True`: 사용자가 창을 닫으면 워커도 자동 정리.

#### 파일 선택 다이얼로그 — `tkinter.filedialog`

```python
file_path = filedialog.asksaveasfilename(
    title='검색 결과 내보내기',
    defaultextension='.txt',
    initialfile=default_name,
    filetypes=[('텍스트 파일', '*.txt'), ('모든 파일', '*.*')],
)
```

- `filedialog.asksaveasfilename`: OS 네이티브 "다른 이름으로 저장" 다이얼로그. 사용자가 저장 위치/이름을 자유롭게 결정.
- `filetypes` 인자로 확장자 필터를 노출 → 사용성↑.

#### 메시지 박스 — `tkinter.messagebox`

```python
messagebox.showinfo('JAVIS', '녹음이 저장되었습니다.\n\n' + os.path.basename(file_path))
messagebox.showerror('JAVIS', message)
messagebox.askyesno('STT 변환', f'{wav_name} 파일을 STT 변환하시겠습니까?')
```

- `showinfo / showerror / askyesno`: 상황별 적절한 아이콘/색상이 자동 적용되는 OS 네이티브 다이얼로그. `print()`로 콘솔에 띄우는 것보다 명확하고 사용자가 놓치지 않음.

---

## 4. 진입점 — GUI 우선, CLI 폴백

```python
if __name__ == '__main__':
    use_cli = len(sys.argv) > 1 and sys.argv[1] in ('--cli', '-c')
    if use_cli:
        main()
    elif TK_AVAILABLE:
        launch_gui()
    else:
        print('tkinter를 사용할 수 없는 환경이므로 CLI 메뉴로 실행합니다.')
        main()
```

- `python javis.py` → GUI 자동 실행 (한송희 박사의 기본 사용 경로).
- `python javis.py --cli` → 명시적으로 CLI 메뉴 호출 (서버/원격 SSH 환경).
- tkinter 미설치 환경에서는 자동으로 CLI 폴백 → 어떤 환경에서도 멈추지 않고 동작.

---
