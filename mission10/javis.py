# 화성 기지 음성 기록 시스템 - JAVIS
# 10번 과제 - 마이크 인식 및 음성 녹음


import os
import sys
import wave
import datetime
import threading

try:
    import pyaudio
except ImportError:
    print('오류: pyaudio 라이브러리가 필요합니다.')
    print('설치 명령어: pip install pyaudio')
    sys.exit(1)


# 녹음 설정 상수
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORDS_DIR = 'records'


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
    """현재 날짜와 시간을 기반으로 파일 이름을 생성한다.

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

    # 마이크 탐색 및 기본 장치 확인
    input_device = get_microphone_info(audio)
    if input_device is None:
        print('오류: 사용 가능한 마이크가 없어 녹음을 시작할 수 없습니다.')
        audio.terminate()
        return

    print('\n[녹음 안내] 녹음을 시작합니다. 종료하려면 Enter 키를 누르세요.')

    frames = []
    is_recording = [True]  # 리스트로 감싸 스레드에서 수정 가능하게 처리

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


def list_recordings_by_date(start_date_str, end_date_str):
    """특정 날짜 범위에 해당하는 녹음 파일 목록을 출력한다. (보너스 과제)

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
            # 날짜 형식이 다른 파일은 건너뜀
            continue

    if found_files:
        for file_name, file_datetime in found_files:
            formatted = file_datetime.strftime('%Y년 %m월 %d일  %H:%M:%S')
            print(f'  {formatted}  →  {file_name}')
        print(f'\n  총 {len(found_files)}개의 파일을 찾았습니다.')
    else:
        print('  해당 날짜 범위의 녹음 파일이 없습니다.')


def main():
    """JAVIS 메인 실행 함수."""
    print('=' * 50)
    print('  JAVIS - 화성 기지 음성 기록 시스템')
    print('=' * 50)

    while True:
        print('\n[메뉴]')
        print('  1. 음성 녹음 시작')
        print('  2. 날짜 범위로 녹음 파일 검색')
        print('  3. 종료')

        choice = input('\n선택: ').strip()

        if choice == '1':
            record_audio()
        elif choice == '2':
            start = input('시작 날짜 입력 (YYYYMMDD): ').strip()
            end = input('종료 날짜 입력 (YYYYMMDD): ').strip()
            list_recordings_by_date(start, end)
        elif choice == '3':
            print('\n[종료] JAVIS를 종료합니다.')
            break
        else:
            print('올바른 메뉴 번호(1~3)를 선택하세요.')


if __name__ == '__main__':
    main()
