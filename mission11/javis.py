
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

# tkinter는 Python 표준 라이브러리이지만 일부 환경에서 누락될 수 있다.
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False


# 녹음 설정 상수
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORDS_DIR = 'records'
STT_CHUNK_SECONDS = 30  # 구글 STT 호출 시 분할 단위 (초)
BOOKMARKS_FILE = 'bookmarks.json'  # 즐겨찾기(별표) 영속 저장 파일


# ──────────────────────────────────────────
# 공통 유틸리티
# ──────────────────────────────────────────

def create_records_dir():
    """records 폴더가 없으면 생성한다."""
    try:
        if not os.path.exists(RECORDS_DIR):
            os.makedirs(RECORDS_DIR)
            print(f'[폴더 생성] {RECORDS_DIR} 폴더를 생성했습니다.')
    except PermissionError:
        print(f'오류: {RECORDS_DIR} 폴더를 생성할 권한이 없습니다.')
        sys.exit(1)
    except Exception as e:
        print(f'오류: 폴더 생성 중 문제가 발생했습니다 → {e}')
        sys.exit(1)


def seconds_to_time_str(total_seconds):
    """초(float)를 HH:MM:SS 형식의 문자열로 변환한다.

    Args:
        total_seconds (float): 변환할 초 단위 시간

    Returns:
        str: 'HH:MM:SS' 형식 문자열 (예: 00:01:30)
    """
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


# ──────────────────────────────────────────
# 녹음 기능 (10번 과제)
# ──────────────────────────────────────────

def get_microphone_info(audio):
    """시스템에서 사용 가능한 마이크 목록을 출력하고 기본 입력 장치 인덱스를 반환한다.

    Args:
        audio (pyaudio.PyAudio): PyAudio 인스턴스

    Returns:
        int or None: 기본 마이크 장치 인덱스, 마이크 없을 시 None
    """
    device_count = audio.get_device_count()
    print('\n[마이크 탐색] 시스템에서 사용 가능한 입력 장치:')

    has_input = False
    for i in range(device_count):
        device_info = audio.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:
            print(f'  장치 [{i}] : {device_info["name"]}')
            has_input = True

    if not has_input:
        print('  사용 가능한 마이크를 찾을 수 없습니다.')
        return None

    try:
        default_info = audio.get_default_input_device_info()
        print(f'\n[기본 마이크] {default_info["name"]}')
        return int(default_info['index'])
    except IOError:
        print('오류: 기본 마이크 장치를 가져올 수 없습니다.')
        return None


def generate_filename():
    """현재 날짜와 시간을 기반으로 WAV 파일 이름을 생성한다.

    Returns:
        str: '년월일-시간분초.wav' 형식의 파일 이름 (예: 20260507-143022.wav)
    """
    now = datetime.datetime.now()
    return now.strftime('%Y%m%d-%H%M%S') + '.wav'


def save_wav_file(file_path, audio, frames):
    """녹음된 데이터를 WAV 파일로 저장한다.

    Args:
        file_path (str): 저장할 파일 경로
        audio (pyaudio.PyAudio): PyAudio 인스턴스 (샘플 크기 참조용)
        frames (list): 녹음된 오디오 데이터 청크 목록
    """
    try:
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        print(f'\n[저장 완료] {file_path}')
    except PermissionError:
        print(f'오류: 파일 저장 권한이 없습니다 → {file_path}')
    except Exception as e:
        print(f'오류: 파일 저장 중 문제가 발생했습니다 → {e}')


def record_audio():
    """시스템 마이크를 인식하고 음성을 녹음하여 records 폴더에 저장한다.

    Enter 키를 누르면 녹음이 종료되고 파일이 저장된다.
    파일명은 녹음 시작 시각 기준으로 '년월일-시간분초.wav' 형식으로 저장된다.
    """
    create_records_dir()

    audio = pyaudio.PyAudio()
    input_device = get_microphone_info(audio)

    if input_device is None:
        print('오류: 사용 가능한 마이크가 없어 녹음을 시작할 수 없습니다.')
        audio.terminate()
        return

    print('\n[녹음 안내] 녹음을 시작합니다. 종료하려면 Enter 키를 누르세요.')

    frames = []
    is_recording = [True]

    def stop_on_enter():
        """Enter 키 입력을 감지하여 녹음을 중단하는 스레드 함수."""
        input()
        is_recording[0] = False

    stop_thread = threading.Thread(target=stop_on_enter, daemon=True)
    stop_thread.start()

    try:
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=CHUNK
        )

        print('[녹음 중] ● (Enter 키로 중지)\n')

        while is_recording[0]:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()

    except OSError as e:
        print(f'오류: 마이크 스트림을 열 수 없습니다 → {e}')
        audio.terminate()
        return
    except Exception as e:
        print(f'오류: 녹음 중 예기치 않은 문제가 발생했습니다 → {e}')
        audio.terminate()
        return

    file_name = generate_filename()
    file_path = os.path.join(RECORDS_DIR, file_name)
    save_wav_file(file_path, audio, frames)
    audio.terminate()


def record_audio_with_event(stop_event, status_callback=None):
    """GUI/스레드용 녹음 함수. stop_event가 set될 때까지 녹음한다.

    CLI용 record_audio()와 달리 input() 대신 threading.Event로
    종료 신호를 받기 때문에 GUI 메인 루프와 함께 사용할 수 있다.
    오디오 자원은 try/finally로 반드시 해제된다.

    Args:
        stop_event (threading.Event): set 되면 녹음 종료.
        status_callback (callable, optional): 경과 시간(초)을 받는 콜백.

    Returns:
        tuple: (성공 여부 bool, 파일 경로 str 또는 None, 메시지 str)
    """
    create_records_dir()

    audio = pyaudio.PyAudio()
    stream = None
    frames = []

    try:
        try:
            default_info = audio.get_default_input_device_info()
            input_device = int(default_info['index'])
        except IOError:
            return False, None, '사용 가능한 마이크를 찾을 수 없습니다.'

        try:
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=CHUNK,
            )
        except OSError as e:
            return False, None, f'마이크 스트림을 열 수 없습니다 → {e}'

        try:
            frames_per_second = RATE / CHUNK
            chunk_index = 0
            while not stop_event.is_set():
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                chunk_index += 1
                if status_callback is not None and chunk_index % 10 == 0:
                    elapsed = chunk_index / frames_per_second
                    status_callback(elapsed)
        except Exception as e:
            return False, None, f'녹음 중 오류가 발생했습니다 → {e}'

        if not frames:
            return False, None, '녹음된 데이터가 없습니다.'

        file_name = generate_filename()
        file_path = os.path.join(RECORDS_DIR, file_name)

        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
        except OSError as e:
            return False, None, f'파일 저장 중 오류 → {e}'

        return True, file_path, f'녹음 저장 완료: {file_name}'

    finally:
        # 어떤 상황에서도 오디오 자원을 정리한다.
        if stream is not None:
            try:
                stream.stop_stream()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass
        try:
            audio.terminate()
        except Exception:
            pass


def filter_wav_files_by_date(file_names, start_date_str, end_date_str):
    """WAV 파일명 목록을 날짜 범위로 필터링한다.

    Args:
        file_names (list): 'YYYYMMDD-HHMMSS.wav' 형식의 파일명 목록.
        start_date_str (str): YYYYMMDD 형식 시작 날짜.
        end_date_str (str): YYYYMMDD 형식 종료 날짜.

    Returns:
        tuple: (필터된 목록 list, 오류 메시지 str 또는 빈 문자열)
    """
    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y%m%d')
        end_date = datetime.datetime.strptime(end_date_str, '%Y%m%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        return [], '날짜 형식이 올바르지 않습니다 (YYYYMMDD).'

    if start_date > end_date:
        return [], '시작 날짜가 종료 날짜보다 늦을 수 없습니다.'

    matched = []
    for file_name in file_names:
        if not file_name.endswith('.wav'):
            continue
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


def list_recordings_by_date(start_date_str, end_date_str):
    """특정 날짜 범위에 해당하는 녹음 파일 목록을 출력한다.

    Args:
        start_date_str (str): 검색 시작 날짜 (형식: YYYYMMDD)
        end_date_str (str): 검색 종료 날짜 (형식: YYYYMMDD)
    """
    if not os.path.exists(RECORDS_DIR):
        print('[알림] records 폴더가 없습니다. 아직 녹음된 파일이 없습니다.')
        return

    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y%m%d')
        end_date = datetime.datetime.strptime(end_date_str, '%Y%m%d')
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        print('오류: 날짜 형식이 올바르지 않습니다. YYYYMMDD 형식으로 입력하세요.')
        return

    if start_date > end_date:
        print('오류: 시작 날짜가 종료 날짜보다 늦을 수 없습니다.')
        return

    print(f'\n[날짜 검색] {start_date_str} ~ {end_date_str} 범위의 녹음 파일:')

    found_files = []

    try:
        file_list = sorted(os.listdir(RECORDS_DIR))
    except Exception as e:
        print(f'오류: 폴더를 읽는 중 문제가 발생했습니다 → {e}')
        return

    for file_name in file_list:
        if not file_name.endswith('.wav'):
            continue
        try:
            name_without_ext = file_name.replace('.wav', '')
            file_datetime = datetime.datetime.strptime(
                name_without_ext, '%Y%m%d-%H%M%S'
            )
            if start_date <= file_datetime <= end_date:
                found_files.append((file_name, file_datetime))
        except ValueError:
            continue

    if found_files:
        for file_name, file_datetime in found_files:
            formatted = file_datetime.strftime('%Y년 %m월 %d일  %H:%M:%S')
            print(f'  {formatted}  →  {file_name}')
        print(f'\n  총 {len(found_files)}개의 파일을 찾았습니다.')
    else:
        print('  해당 날짜 범위의 녹음 파일이 없습니다.')


# ──────────────────────────────────────────
# STT 기능 (11번 과제)
# ──────────────────────────────────────────

def list_audio_files():
    """records 폴더에 있는 WAV 파일 목록을 반환한다.

    Returns:
        list: WAV 파일명 문자열 목록 (정렬됨), 파일 없을 시 빈 리스트
    """
    if not os.path.exists(RECORDS_DIR):
        print('[알림] records 폴더가 없습니다. 아직 녹음된 파일이 없습니다.')
        return []

    try:
        wav_files = sorted([
            f for f in os.listdir(RECORDS_DIR)
            if f.endswith('.wav')
        ])
    except Exception as e:
        print(f'오류: 폴더를 읽는 중 문제가 발생했습니다 → {e}')
        return []

    return wav_files


def split_wav_to_chunks(wav_path):
    """WAV 파일을 일정 초 단위로 분할하여 (시작 시각(초), AudioData) 목록 반환.

    STT_CHUNK_SECONDS 상수 기준으로 오디오를 나눈다. 구글 STT API는
    한 번에 너무 긴 오디오를 받으면 정확도가 떨어지고 타임아웃이 나기
    쉽기 때문에 30초 단위로 잘라 보낸다.

    Args:
        wav_path (str): 분할할 WAV 파일 경로.

    Returns:
        list of tuple: [(시작초(float), sr.AudioData), ...], 실패 시 빈 리스트.
    """
    chunks = []

    try:
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
                audio_data = sr.AudioData(
                    raw_data, frame_rate, sample_width
                )
                start_seconds = offset / frame_rate
                chunks.append((start_seconds, audio_data))
                offset += frames_per_chunk

    except FileNotFoundError:
        print(f'오류: 파일을 찾을 수 없습니다 → {wav_path}')
    except wave.Error as e:
        print(f'오류: WAV 파일을 읽는 중 문제가 발생했습니다 → {e}')
    except Exception as e:
        print(f'오류: 예기치 않은 문제가 발생했습니다 → {e}')

    return chunks


def transcribe_audio_file(wav_path):
    """WAV 파일을 구글 STT로 변환하여 (시간, 텍스트) 목록을 반환한다.

    오디오를 STT_CHUNK_SECONDS 단위로 나누어 Google Web Speech API로
    인식하고, 각 구간의 시작 시각과 인식된 텍스트를 반환한다.
    인터넷 연결이 필요하다.

    Args:
        wav_path (str): 변환할 WAV 파일 경로.

    Returns:
        list of tuple: [('HH:MM:SS', '인식된 텍스트'), ...], 실패 시 빈 리스트.
    """
    recognizer = sr.Recognizer()
    chunks = split_wav_to_chunks(wav_path)
    results = []

    if not chunks:
        return results

    print(f'\n[STT 시작] {os.path.basename(wav_path)} 변환 중...')

    for start_seconds, audio_data in chunks:
        time_str = seconds_to_time_str(start_seconds)

        try:
            text = recognizer.recognize_google(
                audio_data, language='ko-KR'
            )
            print(f'  [{time_str}] {text}')
            results.append((time_str, text))

        except sr.UnknownValueError:
            # 해당 구간에서 음성을 인식하지 못한 경우 건너뜀
            print(f'  [{time_str}] (음성 인식 불가)')

        except sr.RequestError as e:
            print(f'오류: STT 서비스에 접근할 수 없습니다 → {e}')
            print('      인터넷 연결을 확인하거나 잠시 후 다시 시도하세요.')
            break

    return results


def save_stt_csv(wav_file_name, stt_results):
    """STT 변환 결과를 CSV 파일로 저장한다.

    파일명은 WAV 파일과 동일하고 확장자만 .csv로 변경한다.
    CSV 형식: 시간, 인식된 텍스트

    Args:
        wav_file_name (str): 원본 WAV 파일 이름 (경로 제외)
        stt_results (list): [(시간 문자열, 텍스트), ...] 형태의 STT 결과 목록
    """
    if not stt_results:
        print('[알림] 저장할 STT 결과가 없습니다.')
        return

    csv_file_name = wav_file_name.replace('.wav', '.csv')
    csv_path = os.path.join(RECORDS_DIR, csv_file_name)

    try:
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['시간', '인식된 텍스트'])
            writer.writerows(stt_results)
        print(f'[CSV 저장 완료] {csv_path}')

    except PermissionError:
        print(f'오류: CSV 파일 저장 권한이 없습니다 → {csv_path}')
    except Exception as e:
        print(f'오류: CSV 저장 중 문제가 발생했습니다 → {e}')


def process_all_recordings():
    """records 폴더의 모든 WAV 파일을 STT 변환하고 각각 CSV로 저장한다.

    이미 CSV가 존재하는 파일은 건너뛴다.
    """
    wav_files = list_audio_files()

    if not wav_files:
        print('[알림] 변환할 녹음 파일이 없습니다.')
        return

    print(f'\n[파일 목록] records 폴더의 녹음 파일 ({len(wav_files)}개):')
    for idx, file_name in enumerate(wav_files, start=1):
        print(f'  [{idx}] {file_name}')

    print('\n모든 파일을 STT 변환합니다.')

    for file_name in wav_files:
        csv_name = file_name.replace('.wav', '.csv')
        csv_path = os.path.join(RECORDS_DIR, csv_name)

        if os.path.exists(csv_path):
            print(f'\n[건너뜀] 이미 CSV가 존재합니다 → {csv_name}')
            continue

        wav_path = os.path.join(RECORDS_DIR, file_name)
        stt_results = transcribe_audio_file(wav_path)
        save_stt_csv(file_name, stt_results)

    print('\n[완료] 모든 파일의 STT 변환이 끝났습니다.')


def process_single_recording():
    """사용자가 선택한 WAV 파일 하나를 STT 변환하고 CSV로 저장한다."""
    wav_files = list_audio_files()

    if not wav_files:
        print('[알림] 변환할 녹음 파일이 없습니다.')
        return

    print(f'\n[파일 목록] records 폴더의 녹음 파일:')
    for idx, file_name in enumerate(wav_files, start=1):
        print(f'  [{idx}] {file_name}')

    try:
        choice = input('\n변환할 파일 번호를 선택하세요: ').strip()
        selected_idx = int(choice) - 1

        if not 0 <= selected_idx < len(wav_files):
            print('오류: 올바른 번호를 선택하세요.')
            return

    except ValueError:
        print('오류: 숫자를 입력해야 합니다.')
        return

    file_name = wav_files[selected_idx]
    wav_path = os.path.join(RECORDS_DIR, file_name)
    stt_results = transcribe_audio_file(wav_path)
    save_stt_csv(file_name, stt_results)


# ──────────────────────────────────────────
# 키워드 검색 기능 (보너스 과제)
# ──────────────────────────────────────────

def search_keyword_in_csv(keyword):
    """저장된 모든 CSV 파일에서 키워드가 포함된 내용을 찾아 출력한다.

    Args:
        keyword (str): 검색할 키워드 문자열
    """
    if not os.path.exists(RECORDS_DIR):
        print('[알림] records 폴더가 없습니다.')
        return

    try:
        csv_files = sorted([
            f for f in os.listdir(RECORDS_DIR)
            if f.endswith('.csv')
        ])
    except Exception as e:
        print(f'오류: 폴더를 읽는 중 문제가 발생했습니다 → {e}')
        return

    if not csv_files:
        print('[알림] 검색할 CSV 파일이 없습니다. 먼저 STT 변환을 실행하세요.')
        return

    print(f'\n[키워드 검색] "{keyword}" 검색 중...')

    total_found = 0

    for csv_file_name in csv_files:
        csv_path = os.path.join(RECORDS_DIR, csv_file_name)
        found_in_file = []

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as csv_file:
                reader = csv.reader(csv_file)
                next(reader, None)  # 헤더 행 건너뜀

                for row in reader:
                    if len(row) < 2:
                        continue
                    time_str, text = row[0], row[1]
                    if keyword.lower() in text.lower():
                        found_in_file.append((time_str, text))

        except FileNotFoundError:
            print(f'오류: 파일을 찾을 수 없습니다 → {csv_path}')
            continue
        except Exception as e:
            print(f'오류: 파일 읽기 중 문제가 발생했습니다 → {e}')
            continue

        if found_in_file:
            print(f'\n  📄 {csv_file_name}')
            for time_str, text in found_in_file:
                print(f'     [{time_str}] {text}')
            total_found += len(found_in_file)

    if total_found > 0:
        print(f'\n  총 {total_found}건의 결과를 찾았습니다.')
    else:
        print(f'  "{keyword}"와 일치하는 내용이 없습니다.')


# ──────────────────────────────────────────
# 북마크 (즐겨찾기) 영속 저장
# ──────────────────────────────────────────

def load_bookmarks():
    """저장된 북마크 데이터를 dict로 반환한다.

    Returns:
        dict: { 'CSV파일명': ['HH:MM:SS', ...] } 구조의 dict.
              파일이 없거나 오류 발생 시 빈 dict 반환.
    """
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
    """북마크 dict를 JSON 파일로 저장한다.

    Args:
        bookmarks (dict): 저장할 북마크 데이터.
    """
    try:
        with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as bm_file:
            json.dump(bookmarks, bm_file, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f'오류: 북마크 저장에 실패했습니다 → {e}')


def toggle_bookmark(bookmarks, csv_file, time_str):
    """특정 (csv_file, time_str) 항목의 북마크 상태를 토글한다.

    Args:
        bookmarks (dict): 북마크 데이터 dict (in-place 변경).
        csv_file (str): CSV 파일 이름.
        time_str (str): 발화 시작 시간 문자열.

    Returns:
        bool: 토글 후 북마크 여부 (True=북마크됨, False=해제됨).
    """
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


def is_bookmarked(bookmarks, csv_file, time_str):
    """해당 항목이 북마크되어 있는지 여부를 반환한다."""
    return time_str in bookmarks.get(csv_file, [])


# ──────────────────────────────────────────
# CSV 읽기 / 통계 / 내보내기 헬퍼
# ──────────────────────────────────────────

def list_csv_files():
    """records 폴더의 CSV 파일 이름 목록을 정렬해서 반환한다."""
    if not os.path.exists(RECORDS_DIR):
        return []

    try:
        return sorted([
            f for f in os.listdir(RECORDS_DIR)
            if f.endswith('.csv')
        ])
    except OSError as e:
        print(f'오류: CSV 목록을 읽을 수 없습니다 → {e}')
        return []


def read_csv_entries(csv_file_name):
    """CSV 한 파일에서 (시간, 텍스트) 목록을 읽어 반환한다.

    Args:
        csv_file_name (str): records 폴더 안의 CSV 파일 이름.

    Returns:
        list of tuple: [(time_str, text), ...]
    """
    csv_path = os.path.join(RECORDS_DIR, csv_file_name)
    entries = []

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as csv_file:
            reader = csv.reader(csv_file)
            next(reader, None)  # 헤더 건너뜀
            for row in reader:
                if len(row) >= 2:
                    entries.append((row[0], row[1]))
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f'오류: CSV 파일 읽기 실패 → {e}')

    return entries


def collect_statistics(bookmarks):
    """JAVIS 사용 통계를 계산해 dict로 반환한다.

    Args:
        bookmarks (dict): 북마크 데이터 dict.

    Returns:
        dict: 통계 정보가 담긴 dict.
    """
    wav_files = list_audio_files()
    csv_files = list_csv_files()
    wav_set = {name.replace('.wav', '') for name in wav_files}
    csv_set = {name.replace('.csv', '') for name in csv_files}

    transcribed = len(wav_set & csv_set)
    not_transcribed = len(wav_set - csv_set)

    total_utterances = 0
    total_chars = 0
    for csv_name in csv_files:
        entries = read_csv_entries(csv_name)
        total_utterances += len(entries)
        for _, text in entries:
            total_chars += len(text)

    bookmark_count = sum(len(times) for times in bookmarks.values())

    return {
        'wav_count': len(wav_files),
        'csv_count': len(csv_files),
        'transcribed': transcribed,
        'not_transcribed': not_transcribed,
        'utterances': total_utterances,
        'chars': total_chars,
        'bookmarks': bookmark_count,
    }


def export_results_to_txt(file_path, results, keyword=None):
    """검색 결과/북마크 결과를 텍스트 파일로 저장한다.

    Args:
        file_path (str): 저장할 .txt 파일 경로.
        results (list): [(csv_file, time_str, text), ...] 형태 결과.
        keyword (str, optional): 머리말에 표기할 검색 키워드.

    Returns:
        bool: 성공 시 True, 실패 시 False.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as out_file:
            out_file.write('JAVIS - 화성 기지 음성 기록 검색 결과\n')
            out_file.write('=' * 50 + '\n')
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            out_file.write(f'내보낸 시각: {now_str}\n')
            if keyword:
                out_file.write(f'검색 키워드: {keyword}\n')
            out_file.write(f'총 결과 수: {len(results)}건\n')
            out_file.write('=' * 50 + '\n\n')

            current_file = None
            for csv_file, time_str, text in results:
                if csv_file != current_file:
                    out_file.write(f'\n[파일] {csv_file}\n')
                    out_file.write('-' * 50 + '\n')
                    current_file = csv_file
                out_file.write(f'  [{time_str}]  {text}\n')

        return True
    except OSError as e:
        print(f'오류: 텍스트 파일 저장 실패 → {e}')
        return False


# ──────────────────────────────────────────
# GUI (tkinter) - 보너스 과제
# ──────────────────────────────────────────

class JavisGUI:
    """JAVIS 음성 기록 검색용 tkinter GUI 애플리케이션.

    표준 라이브러리만 사용해서 키워드 검색, 북마크, 통계, 내보내기 기능을
    사용자 친화적인 화면으로 제공한다.
    """

    BOOKMARK_ON = '★'
    BOOKMARK_OFF = '☆'

    # 컬러 팔레트 (한송희 박사의 화성 일지 무드)
    COLOR_BG = '#F4F6FA'
    COLOR_PANEL = '#FFFFFF'
    COLOR_FG = '#2D3142'
    COLOR_PRIMARY = '#3D5A80'
    COLOR_ACCENT = '#EE6C4D'
    COLOR_SUCCESS = '#2A9D8F'
    COLOR_DANGER = '#E63946'
    COLOR_MUTED = '#6C757D'
    COLOR_HIGHLIGHT = '#FFF3B0'
    COLOR_BOOKMARK = '#D4A82B'
    COLOR_ALT_ROW = '#F9FAFC'
    COLOR_BORDER = '#DEE2E6'
    COLOR_HEADER_BG = '#3D5A80'
    COLOR_HEADER_FG = '#FFFFFF'

    def __init__(self, root):
        """GUI를 초기화한다.

        Args:
            root (tk.Tk): tkinter 루트 윈도우.
        """
        self.root = root
        self.bookmarks = load_bookmarks()
        # 현재 트리뷰에 표시 중인 결과: [(csv_file, time_str, text), ...]
        self.current_results = []
        # 현재 검색 키워드 (내보내기 시 머리말로 사용)
        self.current_keyword = ''
        # 북마크만 보기 토글
        self.show_only_bookmarks = tk.BooleanVar(value=False)
        # 녹음 상태
        self.is_recording = False
        self.record_stop_event = None
        # 날짜 필터: None 이거나 (start_str, end_str) 튜플
        self.date_filter = None

        self._setup_styles()
        self._build_ui()
        self.refresh_file_list()
        self.show_all_entries()

        # 창이 모두 그려진 다음 검색창에 포커스를 준다.
        self.root.after(150, self._focus_search_entry)
        # 창을 닫을 때 녹음 중이면 안전하게 정리한다.
        self.root.protocol('WM_DELETE_WINDOW', self._on_window_close)

    def _focus_search_entry(self):
        """검색 입력란에 포커스를 강제한다 (macOS Korean IME 호환)."""
        try:
            self.search_entry.focus_force()
            self.search_entry.icursor(tk.END)
        except Exception:
            pass

    def _on_window_close(self):
        """창 닫기 처리. 녹음 중이면 종료 신호를 먼저 보낸다."""
        if self.is_recording and self.record_stop_event is not None:
            self.record_stop_event.set()
        self.root.destroy()

    def _setup_styles(self):
        """ttk 테마와 위젯 스타일을 설정한다."""
        self.root.configure(bg=self.COLOR_BG)

        style = ttk.Style()
        # 커스터마이징이 가장 잘 되는 'clam'을 우선 사용한다.
        available = style.theme_names()
        for preferred in ('clam', 'alt', 'default'):
            if preferred in available:
                try:
                    style.theme_use(preferred)
                except tk.TclError:
                    continue
                break

        base_font = ('TkDefaultFont', 11)
        bold_font = ('TkDefaultFont', 11, 'bold')

        style.configure('TFrame', background=self.COLOR_BG)
        style.configure(
            'Panel.TFrame',
            background=self.COLOR_PANEL,
            relief='flat',
        )
        style.configure(
            'Header.TFrame', background=self.COLOR_HEADER_BG
        )

        style.configure(
            'TLabel',
            background=self.COLOR_BG,
            foreground=self.COLOR_FG,
            font=base_font,
        )
        style.configure(
            'HeaderTitle.TLabel',
            background=self.COLOR_HEADER_BG,
            foreground=self.COLOR_HEADER_FG,
            font=('TkDefaultFont', 18, 'bold'),
        )
        style.configure(
            'HeaderSubtitle.TLabel',
            background=self.COLOR_HEADER_BG,
            foreground='#C0CFE2',
            font=('TkDefaultFont', 10),
        )
        style.configure(
            'Section.TLabel',
            background=self.COLOR_BG,
            foreground=self.COLOR_PRIMARY,
            font=bold_font,
        )
        style.configure(
            'Filter.TLabel',
            background=self.COLOR_BG,
            foreground=self.COLOR_PRIMARY,
            font=('TkDefaultFont', 10, 'bold'),
        )
        style.configure(
            'Status.TLabel',
            background='#E8ECEF',
            foreground=self.COLOR_FG,
            font=base_font,
            padding=(10, 6),
        )

        style.configure(
            'TButton', padding=(12, 7), font=base_font
        )
        style.configure(
            'Record.TButton',
            padding=(14, 8),
            foreground=self.COLOR_SUCCESS,
            font=bold_font,
        )
        style.map(
            'Record.TButton',
            foreground=[('active', self.COLOR_SUCCESS)],
        )
        style.configure(
            'Recording.TButton',
            padding=(14, 8),
            foreground=self.COLOR_DANGER,
            font=bold_font,
        )
        style.map(
            'Recording.TButton',
            foreground=[('active', self.COLOR_DANGER)],
        )
        style.configure(
            'Primary.TButton',
            padding=(14, 8),
            foreground=self.COLOR_PRIMARY,
            font=bold_font,
        )

        style.configure(
            'TCheckbutton',
            background=self.COLOR_BG,
            foreground=self.COLOR_FG,
            font=base_font,
        )
        style.configure(
            'TLabelframe',
            background=self.COLOR_BG,
            bordercolor=self.COLOR_BORDER,
        )
        style.configure(
            'TLabelframe.Label',
            background=self.COLOR_BG,
            foreground=self.COLOR_PRIMARY,
            font=bold_font,
        )
        style.configure('TSeparator', background=self.COLOR_BORDER)
        style.configure('TPanedwindow', background=self.COLOR_BG)

        # Treeview
        style.configure(
            'Treeview',
            rowheight=30,
            font=base_font,
            background=self.COLOR_PANEL,
            fieldbackground=self.COLOR_PANEL,
            foreground=self.COLOR_FG,
            borderwidth=0,
        )
        style.configure(
            'Treeview.Heading',
            font=bold_font,
            background='#E8ECEF',
            foreground=self.COLOR_FG,
            padding=(8, 6),
            relief='flat',
        )
        style.map(
            'Treeview',
            background=[('selected', '#B8D4F1')],
            foreground=[('selected', self.COLOR_FG)],
        )

    # ── 화면 구성 ───────────────────────────────────────

    def _build_ui(self):
        """전체 위젯을 구성한다."""
        self.root.title('JAVIS - 화성 기지 음성 기록 시스템')
        self.root.geometry('1180x720')
        self.root.minsize(960, 580)

        self._build_header()
        self._build_toolbar()
        self._build_main_pane()
        self._build_statusbar()

    def _build_header(self):
        """상단 헤더 바를 그린다."""
        header = ttk.Frame(self.root, style='Header.TFrame')
        header.pack(side=tk.TOP, fill=tk.X)

        inner = ttk.Frame(
            header, style='Header.TFrame', padding=(20, 14, 20, 14)
        )
        inner.pack(fill=tk.X)

        title = ttk.Label(
            inner,
            text='🛰  JAVIS',
            style='HeaderTitle.TLabel',
        )
        title.pack(side=tk.LEFT)

        subtitle = ttk.Label(
            inner,
            text='   화성 기지 음성 기록 시스템 · 음성에서 문자로',
            style='HeaderSubtitle.TLabel',
        )
        subtitle.pack(side=tk.LEFT, anchor='s', pady=(0, 3))

    def _build_toolbar(self):
        """상단 툴바(액션 버튼 + 검색바)를 두 행으로 생성한다."""
        # ── 1행: 액션 버튼 ───────────────────────────────
        action_bar = ttk.Frame(self.root, padding=(16, 14, 16, 4))
        action_bar.pack(side=tk.TOP, fill=tk.X)

        self.record_btn = ttk.Button(
            action_bar,
            text='🎙  녹음 시작',
            style='Record.TButton',
            command=self.toggle_recording,
        )
        self.record_btn.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Button(
            action_bar,
            text='📅  날짜 검색',
            command=self.show_date_filter_dialog,
        ).pack(side=tk.LEFT, padx=3)

        ttk.Separator(action_bar, orient='vertical').pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        ttk.Button(
            action_bar, text='선택 STT 변환', command=self.run_stt_selected
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            action_bar, text='전체 STT 변환', command=self.run_stt_all
        ).pack(side=tk.LEFT, padx=3)

        ttk.Separator(action_bar, orient='vertical').pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        ttk.Button(
            action_bar, text='📊 통계', command=self.show_statistics
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            action_bar, text='💾 결과 내보내기', command=self.export_results
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            action_bar, text='🔄 새로고침', command=self.refresh_all
        ).pack(side=tk.LEFT, padx=3)

        # ── 2행: 키워드 검색바 ──────────────────────────
        search_bar = ttk.Frame(self.root, padding=(16, 4, 16, 12))
        search_bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(
            search_bar, text='🔍  키워드', style='Filter.TLabel'
        ).pack(side=tk.LEFT, padx=(0, 8))

        # ttk.Entry가 macOS Korean IME와 충돌하는 경우가 있어 tk.Entry 사용.
        self.search_var = tk.StringVar()
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
        self.search_entry.pack(
            side=tk.LEFT, ipady=6, padx=(0, 6)
        )
        self.search_entry.bind('<Return>', lambda e: self.do_search())
        # 클릭하면 확실하게 포커스를 가져온다.
        self.search_entry.bind(
            '<Button-1>',
            lambda e: self.search_entry.focus_set(),
        )

        ttk.Button(
            search_bar,
            text='검색',
            style='Primary.TButton',
            command=self.do_search,
        ).pack(side=tk.LEFT, padx=3)
        ttk.Button(
            search_bar, text='전체 보기', command=self.show_all_entries
        ).pack(side=tk.LEFT, padx=3)

        ttk.Checkbutton(
            search_bar,
            text='⭐ 북마크만',
            variable=self.show_only_bookmarks,
            command=self.apply_bookmark_filter,
        ).pack(side=tk.LEFT, padx=(14, 2))

        # 날짜 필터가 활성화되면 옆에 표시되는 라벨
        self.date_filter_label = ttk.Label(
            search_bar, text='', style='Filter.TLabel'
        )
        self.date_filter_label.pack(side=tk.LEFT, padx=(14, 4))

    def _build_main_pane(self):
        """가운데 영역(좌측 파일 목록 + 우측 결과 트리)을 생성한다."""
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=16, pady=(2, 10))

        # ── 좌측: 파일 목록 ────────────────────────────
        left_frame = ttk.LabelFrame(paned, text='  📁 녹음 파일  ')
        paned.add(left_frame, weight=1)

        list_container = ttk.Frame(left_frame, padding=(2, 4, 2, 4))
        list_container.pack(fill=tk.BOTH, expand=True)

        self.file_listbox = tk.Listbox(
            list_container,
            activestyle='dotbox',
            font=('TkDefaultFont', 11),
            relief='flat',
            highlightthickness=1,
            highlightbackground=self.COLOR_BORDER,
            highlightcolor=self.COLOR_PRIMARY,
            bg=self.COLOR_PANEL,
            fg=self.COLOR_FG,
            selectbackground='#B8D4F1',
            selectforeground=self.COLOR_FG,
            borderwidth=0,
        )
        self.file_listbox.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4
        )
        file_scroll = ttk.Scrollbar(
            list_container,
            orient=tk.VERTICAL,
            command=self.file_listbox.yview,
        )
        file_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=file_scroll.set)
        self.file_listbox.bind(
            '<<ListboxSelect>>', self._on_file_selected
        )

        # ── 우측: 결과 트리뷰 ──────────────────────────
        right_frame = ttk.LabelFrame(
            paned, text='  💬 발화 목록 / 검색 결과  '
        )
        paned.add(right_frame, weight=4)

        tree_container = ttk.Frame(right_frame, padding=(2, 4, 2, 4))
        tree_container.pack(fill=tk.BOTH, expand=True)

        columns = ('star', 'time', 'text', 'file')
        self.tree = ttk.Treeview(
            tree_container, columns=columns, show='headings', height=20
        )
        self.tree.heading('star', text='★')
        self.tree.heading('time', text='시간')
        self.tree.heading('text', text='인식된 텍스트')
        self.tree.heading('file', text='파일')

        self.tree.column(
            'star', width=44, anchor='center', stretch=False
        )
        self.tree.column(
            'time', width=96, anchor='center', stretch=False
        )
        self.tree.column('text', width=580, anchor='w')
        self.tree.column('file', width=200, anchor='w')

        # 행 강조 태그
        self.tree.tag_configure('odd', background=self.COLOR_ALT_ROW)
        self.tree.tag_configure('even', background=self.COLOR_PANEL)
        self.tree.tag_configure('hit', background=self.COLOR_HIGHLIGHT)
        self.tree.tag_configure(
            'bookmarked',
            foreground=self.COLOR_BOOKMARK,
            font=('TkDefaultFont', 11, 'bold'),
        )

        self.tree.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4
        )

        tree_scroll = ttk.Scrollbar(
            tree_container,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=tree_scroll.set)

        # 더블 클릭 / Enter / Space 키로 북마크 토글
        self.tree.bind('<Double-1>', self._on_tree_activate)
        self.tree.bind('<Return>', self._on_tree_activate)
        self.tree.bind('<space>', self._on_tree_activate)

    def _build_statusbar(self):
        """하단 상태바를 생성한다."""
        self.status_var = tk.StringVar(
            value='준비됨 — 검색창에 키워드를 입력하고 Enter 키를 누르세요.'
        )
        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            style='Status.TLabel',
            anchor='w',
        )
        status.pack(side=tk.BOTTOM, fill=tk.X)

    # ── 상태 표시 / 새로고침 ─────────────────────────────

    def set_status(self, message):
        """상태바 메시지를 갱신한다."""
        self.status_var.set(message)
        self.root.update_idletasks()

    def refresh_file_list(self):
        """좌측 파일 목록을 새로고침한다.

        CSV 존재 여부와 북마크 개수를 함께 표시하고,
        날짜 필터가 활성화돼 있으면 적용한다.
        """
        self.file_listbox.delete(0, tk.END)
        wav_files = list_audio_files()

        if self.date_filter is not None:
            start_str, end_str = self.date_filter
            wav_files, _err = filter_wav_files_by_date(
                wav_files, start_str, end_str
            )
            self.date_filter_label.config(
                text=f'📅 {start_str} ~ {end_str}  [필터 해제하려면 클릭]'
            )
            self.date_filter_label.bind(
                '<Button-1>', lambda e: self.clear_date_filter()
            )
        else:
            self.date_filter_label.config(text='')
            self.date_filter_label.unbind('<Button-1>')

        if not wav_files:
            self.file_listbox.insert(tk.END, '  (녹음 파일 없음)')
            return

        for file_name in wav_files:
            csv_name = file_name.replace('.wav', '.csv')
            csv_path = os.path.join(RECORDS_DIR, csv_name)
            csv_mark = '📝' if os.path.exists(csv_path) else '  '
            bm_count = len(self.bookmarks.get(csv_name, []))
            bm_mark = f' ★{bm_count}' if bm_count else ''
            self.file_listbox.insert(
                tk.END, f'{csv_mark} {file_name}{bm_mark}'
            )

    def refresh_all(self):
        """파일 목록과 결과 트리를 모두 다시 그린다."""
        self.bookmarks = load_bookmarks()
        self.refresh_file_list()
        if self.current_keyword:
            self.do_search()
        else:
            self.show_all_entries()
        self.set_status('새로고침 완료')

    # ── 트리뷰 채우기 ────────────────────────────────────

    def _populate_tree(self, results, highlight_keyword=None):
        """결과 리스트를 트리뷰에 채워 넣는다.

        Args:
            results (list): [(csv_file, time_str, text), ...] 형태.
            highlight_keyword (str, optional): 매칭된 행에 강조 태그를 부여.
        """
        self.tree.delete(*self.tree.get_children())
        self.current_results = []

        only_bm = self.show_only_bookmarks.get()
        keyword_lower = (
            highlight_keyword.lower() if highlight_keyword else ''
        )

        row_index = 0
        for csv_file, time_str, text in results:
            bookmarked = is_bookmarked(self.bookmarks, csv_file, time_str)
            if only_bm and not bookmarked:
                continue

            star = self.BOOKMARK_ON if bookmarked else self.BOOKMARK_OFF
            tags = ['odd' if row_index % 2 else 'even']
            if bookmarked:
                tags.append('bookmarked')
            if keyword_lower and keyword_lower in text.lower():
                tags.append('hit')

            self.tree.insert(
                '',
                tk.END,
                values=(star, time_str, text, csv_file),
                tags=tuple(tags),
            )
            self.current_results.append((csv_file, time_str, text))
            row_index += 1

    # ── 액션: 전체 보기 / 검색 / 북마크 필터 ──────────────

    def show_all_entries(self):
        """모든 CSV 파일의 발화를 트리뷰에 표시한다."""
        self.current_keyword = ''
        results = []
        for csv_file in list_csv_files():
            for time_str, text in read_csv_entries(csv_file):
                results.append((csv_file, time_str, text))

        self._populate_tree(results)
        if not results:
            self.set_status('표시할 발화가 없습니다. STT 변환을 먼저 실행하세요.')
        else:
            self.set_status(
                f'전체 발화 {len(self.current_results)}건 표시'
            )

    def do_search(self):
        """검색바의 키워드로 모든 CSV에서 매칭 행을 찾는다."""
        keyword = self.search_var.get().strip()
        self.current_keyword = keyword

        if not keyword:
            self.show_all_entries()
            return

        results = []
        keyword_lower = keyword.lower()
        for csv_file in list_csv_files():
            for time_str, text in read_csv_entries(csv_file):
                if keyword_lower in text.lower():
                    results.append((csv_file, time_str, text))

        self._populate_tree(results, highlight_keyword=keyword)
        if results:
            self.set_status(
                f'"{keyword}" 검색 결과 {len(self.current_results)}건'
            )
        else:
            self.set_status(f'"{keyword}"에 일치하는 발화가 없습니다.')

    def apply_bookmark_filter(self):
        """북마크만 보기 체크박스 상태가 바뀌면 결과를 다시 그린다."""
        if self.current_keyword:
            self.do_search()
        else:
            self.show_all_entries()

    # ── 액션: 파일 선택 / 북마크 토글 ─────────────────────

    def _on_file_selected(self, _event):
        """좌측 파일 목록에서 항목 선택 시 해당 파일의 발화만 보여준다."""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        line = self.file_listbox.get(selection[0])
        # '📝 20260507-203410.wav ★3' 형태에서 파일명만 분리
        parts = line.strip().split()
        wav_name = None
        for token in parts:
            if token.endswith('.wav'):
                wav_name = token
                break
        if wav_name is None:
            return

        csv_name = wav_name.replace('.wav', '.csv')
        csv_path = os.path.join(RECORDS_DIR, csv_name)
        if not os.path.exists(csv_path):
            self._populate_tree([])
            self.set_status(
                f'{wav_name}은 아직 STT 변환되지 않았습니다.'
            )
            return

        self.current_keyword = ''
        results = [
            (csv_name, t, txt) for t, txt in read_csv_entries(csv_name)
        ]
        self._populate_tree(results)
        self.set_status(f'{csv_name} - 발화 {len(results)}건 표시')

    def _on_tree_activate(self, _event):
        """트리뷰 행에서 더블 클릭/Enter/Space 입력 시 북마크를 토글한다."""
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.tree.item(item_id, 'values')
        if len(values) < 4:
            return
        _, time_str, _text, csv_file = values

        now_on = toggle_bookmark(self.bookmarks, csv_file, time_str)
        save_bookmarks(self.bookmarks)

        # 트리뷰 갱신
        star = self.BOOKMARK_ON if now_on else self.BOOKMARK_OFF
        current_vals = list(self.tree.item(item_id, 'values'))
        current_vals[0] = star
        self.tree.item(item_id, values=current_vals)

        tags = list(self.tree.item(item_id, 'tags'))
        if now_on and 'bookmarked' not in tags:
            tags.append('bookmarked')
        if not now_on and 'bookmarked' in tags:
            tags.remove('bookmarked')
        self.tree.item(item_id, tags=tuple(tags))

        # 좌측 파일 목록의 북마크 카운트 갱신
        self.refresh_file_list()
        action = '북마크 추가' if now_on else '북마크 해제'
        self.set_status(f'{action}: [{time_str}] ({csv_file})')

        # 북마크만 보기 상태에서 해제된 경우 즉시 숨김
        if not now_on and self.show_only_bookmarks.get():
            self.tree.delete(item_id)
            self.current_results = [
                r for r in self.current_results
                if not (r[0] == csv_file and r[1] == time_str)
            ]

    # ── 액션: STT 변환 (백그라운드) ───────────────────────

    def run_stt_selected(self):
        """좌측에서 선택된 WAV 파일에 대해 STT 변환을 수행한다."""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showinfo(
                'JAVIS', '먼저 좌측에서 변환할 녹음 파일을 선택하세요.'
            )
            return

        line = self.file_listbox.get(selection[0])
        wav_name = None
        for token in line.strip().split():
            if token.endswith('.wav'):
                wav_name = token
                break
        if wav_name is None:
            return

        if not messagebox.askyesno(
            'STT 변환',
            f'{wav_name} 파일을 STT 변환하시겠습니까?\n'
            '(인터넷 연결과 약간의 시간이 필요합니다.)',
        ):
            return

        self._run_stt_in_thread([wav_name])

    def run_stt_all(self):
        """records 폴더의 모든 WAV 파일에 대해 STT 변환을 수행한다.

        이미 CSV가 존재하는 파일은 건너뛴다.
        """
        wav_files = list_audio_files()
        if not wav_files:
            messagebox.showinfo('JAVIS', '변환할 녹음 파일이 없습니다.')
            return

        pending = []
        for name in wav_files:
            csv_path = os.path.join(
                RECORDS_DIR, name.replace('.wav', '.csv')
            )
            if not os.path.exists(csv_path):
                pending.append(name)

        if not pending:
            messagebox.showinfo(
                'JAVIS', '모든 파일이 이미 STT 변환되어 있습니다.'
            )
            return

        if not messagebox.askyesno(
            'STT 변환',
            f'STT 변환 대상 {len(pending)}개 파일이 있습니다.\n'
            '전체를 변환하시겠습니까?',
        ):
            return

        self._run_stt_in_thread(pending)

    def _run_stt_in_thread(self, wav_files):
        """STT 작업을 백그라운드 스레드에서 실행한다.

        GUI가 멈추지 않도록 별도 스레드에서 변환을 진행하고,
        완료 후 메인 스레드에서 화면을 갱신한다.
        """
        def worker():
            try:
                for idx, file_name in enumerate(wav_files, start=1):
                    self.root.after(
                        0,
                        lambda i=idx, n=file_name, t=len(wav_files):
                        self.set_status(
                            f'STT 변환 중 ({i}/{t}): {n}'
                        ),
                    )
                    wav_path = os.path.join(RECORDS_DIR, file_name)
                    results = transcribe_audio_file(wav_path)
                    save_stt_csv(file_name, results)
            finally:
                self.root.after(0, self._after_stt_finished)

        self.set_status('STT 변환을 시작합니다...')
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _after_stt_finished(self):
        """STT 변환 완료 후 호출되어 화면을 갱신한다."""
        self.refresh_file_list()
        if self.current_keyword:
            self.do_search()
        else:
            self.show_all_entries()
        self.set_status('STT 변환이 완료되었습니다.')
        messagebox.showinfo('JAVIS', 'STT 변환이 완료되었습니다.')

    # ── 액션: 음성 녹음 ─────────────────────────────────

    def toggle_recording(self):
        """녹음 시작/중지 토글."""
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        """백그라운드 스레드에서 녹음을 시작한다."""
        self.record_stop_event = threading.Event()
        self.is_recording = True
        self.record_btn.config(text='● 녹음 중지', style='Recording.TButton')
        self.set_status('녹음 중... ● (00:00:00)')

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
            # 어떤 결과든 메인 스레드에서 반드시 후처리 호출
            self.root.after(
                0,
                lambda: self._after_recording_done(ok, file_path, message),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _stop_recording(self):
        """녹음 종료 신호를 보내고 버튼을 즉시 복구한다."""
        if self.record_stop_event is not None:
            self.record_stop_event.set()
        # 워커 콜백을 기다리지 않고 버튼을 즉시 원래 상태로 복구한다.
        self.is_recording = False
        try:
            self.record_btn.config(text='🎙  녹음 시작', style='Record.TButton')
        except Exception:
            pass
        self.set_status('녹음 종료 중... 파일을 저장합니다.')

    def _after_recording_done(self, ok, file_path, message):
        """녹음 워커가 끝난 뒤 메인 스레드에서 호출되는 후처리.

        어떤 경우에도 녹음 버튼을 원래 상태로 되돌린다.
        """
        # 1) 상태/버튼 복구는 가장 먼저 수행 (이후 단계에서 실패해도 동작)
        self.is_recording = False
        self.record_stop_event = None
        try:
            self.record_btn.config(
                text='🎙  녹음 시작', style='Record.TButton'
            )
            self.root.update_idletasks()
        except Exception:
            pass

        # 2) 화면 업데이트
        try:
            self.set_status(message)
            self.refresh_file_list()
        except Exception:
            pass

        # 3) 결과 알림
        try:
            if ok and file_path:
                messagebox.showinfo(
                    'JAVIS',
                    '녹음이 저장되었습니다.\n\n'
                    + os.path.basename(file_path),
                )
            else:
                messagebox.showerror('JAVIS', message)
        except Exception:
            pass

    # ── 액션: 날짜 범위 검색 ─────────────────────────────

    def show_date_filter_dialog(self):
        """날짜 범위 입력 다이얼로그를 띄워 좌측 파일 목록을 필터링한다."""
        win = tk.Toplevel(self.root)
        win.title('날짜 범위 검색')
        win.geometry('360x250')
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        ttk.Label(
            win,
            text='YYYYMMDD 형식으로 날짜를 입력하세요',
            padding=(12, 12, 12, 4),
        ).pack(anchor='w')

        entry_kwargs = {
            'font': ('TkDefaultFont', 11),
            'relief': 'flat',
            'highlightthickness': 1,
            'highlightbackground': self.COLOR_BORDER,
            'highlightcolor': self.COLOR_PRIMARY,
            'bg': 'white',
            'fg': self.COLOR_FG,
            'insertbackground': self.COLOR_PRIMARY,
            'width': 18,
        }

        body = ttk.Frame(win, padding=(16, 4, 16, 8))
        body.pack(fill=tk.X)

        ttk.Label(body, text='시작 날짜:').grid(
            row=0, column=0, sticky='w', pady=4
        )
        start_var = tk.StringVar()
        start_entry = tk.Entry(
            body, textvariable=start_var, **entry_kwargs
        )
        start_entry.grid(row=0, column=1, sticky='w', padx=8, pady=4, ipady=4)

        ttk.Label(body, text='종료 날짜:').grid(
            row=1, column=0, sticky='w', pady=4
        )
        end_var = tk.StringVar()
        end_entry = tk.Entry(
            body, textvariable=end_var, **entry_kwargs
        )
        end_entry.grid(row=1, column=1, sticky='w', padx=8, pady=4, ipady=4)

        # 기본값: 오늘 날짜로 채워주기
        today = datetime.datetime.now().strftime('%Y%m%d')
        start_var.set(today)
        end_var.set(today)
        start_entry.focus_set()

        msg_var = tk.StringVar()
        ttk.Label(
            body, textvariable=msg_var, foreground='#B00020'
        ).grid(row=2, column=0, columnspan=2, sticky='w', pady=(8, 0))

        def apply_and_close():
            start_str = start_var.get().strip()
            end_str = end_var.get().strip()
            wav_files = list_audio_files()
            _matched, err = filter_wav_files_by_date(
                wav_files, start_str, end_str
            )
            if err:
                msg_var.set('오류: ' + err)
                return
            self.date_filter = (start_str, end_str)
            self.refresh_file_list()
            self.set_status(
                f'날짜 필터 적용: {start_str} ~ {end_str}'
            )
            win.destroy()

        # btn_bar를 body보다 나중에 선언하되, pack 순서를 명시적으로 제어하여
        # 버튼이 항상 화면에 보이도록 한다.
        btn_bar = ttk.Frame(win, padding=(12, 8, 12, 14))
        btn_bar.pack(fill=tk.X)

        ttk.Button(
            btn_bar, text='필터 해제', command=lambda: (
                self.clear_date_filter(), win.destroy()
            )
        ).pack(side=tk.LEFT)
        ttk.Button(
            btn_bar, text='취소', command=win.destroy
        ).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(
            btn_bar, text='적용', command=apply_and_close
        ).pack(side=tk.RIGHT)

        win.bind('<Return>', lambda e: apply_and_close())
        win.bind('<Escape>', lambda e: win.destroy())

    def clear_date_filter(self):
        """날짜 필터를 해제하고 파일 목록을 다시 그린다."""
        self.date_filter = None
        self.refresh_file_list()
        self.set_status('날짜 필터를 해제했습니다.')

    # ── 액션: 통계 / 내보내기 ───────────────────────────

    def show_statistics(self):
        """기록 통계 대시보드 다이얼로그를 표시한다."""
        stats = collect_statistics(self.bookmarks)

        win = tk.Toplevel(self.root)
        win.title('JAVIS 기록 통계')
        win.geometry('420x340')
        win.resizable(False, False)

        title = ttk.Label(
            win,
            text='📊  한송희 박사의 화성 기록',
            font=('TkDefaultFont', 12, 'bold'),
            padding=(12, 12, 12, 4),
        )
        title.pack(anchor='w')

        sub = ttk.Label(
            win,
            text='음성에서 문자로 - 축소된 인류 발전사',
            foreground='#666666',
            padding=(12, 0, 12, 10),
        )
        sub.pack(anchor='w')

        body = ttk.Frame(win, padding=(16, 4, 16, 8))
        body.pack(fill=tk.BOTH, expand=True)

        rows = [
            ('총 녹음 파일', f'{stats["wav_count"]} 개'),
            ('STT 변환 완료', f'{stats["transcribed"]} 개'),
            ('미변환 파일', f'{stats["not_transcribed"]} 개'),
            ('CSV 파일 수', f'{stats["csv_count"]} 개'),
            ('총 발화 수', f'{stats["utterances"]} 줄'),
            ('총 글자 수', f'{stats["chars"]:,} 자'),
            ('북마크된 발화', f'{stats["bookmarks"]} 건'),
        ]

        for i, (label_text, value_text) in enumerate(rows):
            ttk.Label(
                body, text=label_text, anchor='w', width=18
            ).grid(row=i, column=0, sticky='w', pady=3)
            ttk.Label(
                body,
                text=value_text,
                anchor='e',
                font=('TkDefaultFont', 10, 'bold'),
            ).grid(row=i, column=1, sticky='e', pady=3)

        body.columnconfigure(1, weight=1)

        ttk.Button(
            win, text='닫기', command=win.destroy
        ).pack(side=tk.BOTTOM, pady=10)

    def export_results(self):
        """현재 트리뷰의 결과를 .txt 파일로 내보낸다."""
        if not self.current_results:
            messagebox.showinfo('JAVIS', '내보낼 결과가 없습니다.')
            return

        default_name = 'javis_search_'
        if self.current_keyword:
            safe_kw = ''.join(
                ch for ch in self.current_keyword
                if ch.isalnum() or ch in ('-', '_')
            )
            default_name += safe_kw + '_'
        default_name += datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        default_name += '.txt'

        file_path = filedialog.asksaveasfilename(
            title='검색 결과 내보내기',
            defaultextension='.txt',
            initialfile=default_name,
            filetypes=[('텍스트 파일', '*.txt'), ('모든 파일', '*.*')],
        )
        if not file_path:
            return

        ok = export_results_to_txt(
            file_path, self.current_results, keyword=self.current_keyword
        )
        if ok:
            self.set_status(f'내보내기 완료: {file_path}')
            messagebox.showinfo(
                'JAVIS',
                f'검색 결과를 저장했습니다.\n\n{file_path}',
            )
        else:
            messagebox.showerror('JAVIS', '내보내기에 실패했습니다.')


def launch_gui():
    """JAVIS GUI를 실행한다.

    tkinter를 사용할 수 없는 환경이면 안내 메시지를 출력하고 종료한다.
    """
    if not TK_AVAILABLE:
        print('오류: tkinter를 사용할 수 없는 환경입니다.')
        print('  - macOS:  brew install python-tk 또는 공식 Python.org 패키지 사용')
        print('  - Linux:  sudo apt install python3-tk')
        return

    create_records_dir()
    root = tk.Tk()
    JavisGUI(root)
    root.mainloop()


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    """JAVIS 메인 실행 함수."""
    print('=' * 50)
    print('  JAVIS - 화성 기지 음성 기록 시스템')
    print('=' * 50)

    while True:
        print('\n[메뉴]')
        print('  1. 음성 녹음 시작')
        print('  2. 날짜 범위로 녹음 파일 검색')
        print('  3. 선택한 파일 STT 변환 → CSV 저장')
        print('  4. 전체 파일 STT 변환 → CSV 저장')
        print('  5. 키워드 검색 (CLI)')
        print('  6. GUI 검색 창 열기 ')
        print('  7. 종료')

        choice = input('\n선택: ').strip()

        if choice == '1':
            record_audio()
        elif choice == '2':
            start = input('시작 날짜 입력 (YYYYMMDD): ').strip()
            end = input('종료 날짜 입력 (YYYYMMDD): ').strip()
            list_recordings_by_date(start, end)
        elif choice == '3':
            process_single_recording()
        elif choice == '4':
            process_all_recordings()
        elif choice == '5':
            keyword = input('검색할 키워드를 입력하세요: ').strip()
            if keyword:
                search_keyword_in_csv(keyword)
            else:
                print('오류: 키워드를 입력해야 합니다.')
        elif choice == '6':
            launch_gui()
        elif choice == '7':
            print('\n[종료] JAVIS를 종료합니다.')
            break
        else:
            print('올바른 메뉴 번호(1~7)를 선택하세요.')


if __name__ == '__main__':
    # 기본 실행 시 GUI 를 띄운다.
    #   - 'python javis.py'         → GUI 자동 실행 (모든 기능을 GUI 안에서 사용)
    #   - 'python javis.py --cli'   → 기존 터미널 메뉴 사용 (tkinter 미지원 환경용)
    use_cli = len(sys.argv) > 1 and sys.argv[1] in ('--cli', '-c')
    if use_cli:
        main()
    elif TK_AVAILABLE:
        launch_gui()
    else:
        print('tkinter를 사용할 수 없는 환경이므로 CLI 메뉴로 실행합니다.')
        main()
