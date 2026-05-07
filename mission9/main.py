# 카이사르 암호 해독 프로그램
# 9번 과제 - 화성 기지 비상 저장소 잠금 해제


def read_password_file(file_path):
    """password.txt 파일을 읽어 암호문 문자열을 반환한다.

    Args:
        file_path (str): 읽을 파일의 경로

    Returns:
        str or None: 파일 내용(strip 적용) 또는 오류 시 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f'오류: 파일을 찾을 수 없습니다 → {file_path}')
        return None
    except PermissionError:
        print(f'오류: 파일 읽기 권한이 없습니다 → {file_path}')
        return None
    except Exception as e:
        print(f'오류: 파일을 읽는 중 예기치 않은 오류가 발생했습니다 → {e}')
        return None


def save_result_file(file_path, text):
    """해독된 최종 암호를 파일로 저장한다.

    Args:
        file_path (str): 저장할 파일의 경로
        text (str): 저장할 해독 결과 문자열
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(text)
        print(f'\n[저장 완료] 해독된 암호가 "{file_path}" 에 저장되었습니다.')
        print(f'[최종 결과] {text}')
    except PermissionError:
        print(f'오류: 파일 쓰기 권한이 없습니다 → {file_path}')
    except Exception as e:
        print(f'오류: 파일을 저장하는 중 예기치 않은 오류가 발생했습니다 → {e}')


def decode_with_shift(target_text, shift):
    """지정한 자리수(shift)로 카이사르 암호를 해독하여 반환한다.

    알파벳만 이동하고, 공백·숫자·특수문자는 그대로 유지한다.

    Args:
        target_text (str): 해독할 암호 문자열
        shift (int): 0~25 사이의 카이사르 암호 자리수

    Returns:
        str: 해독된 문자열
    """
    decoded_chars = []

    for char in target_text:
        if 'a' <= char <= 'z':
            # 소문자: 자리수만큼 역방향 이동 (모듈러 연산으로 알파벳 범위 유지)
            decoded_chars.append(
                chr(((ord(char) - ord('a') - shift) % 26) + ord('a'))
            )
        elif 'A' <= char <= 'Z':
            # 대문자: 자리수만큼 역방향 이동
            decoded_chars.append(
                chr(((ord(char) - ord('A') - shift) % 26) + ord('A'))
            )
        else:
            # 공백, 숫자, 특수문자는 변환 없이 그대로 유지
            decoded_chars.append(char)

    return ''.join(decoded_chars)


def caesar_cipher_decode(target_text):
    """카이사르 암호를 0~25 자리수로 순서대로 해독하며 결과를 출력한다.

    자리수마다 해독 결과를 눈으로 확인할 수 있도록 출력하고,
    보너스 과제 사전에 있는 단어가 발견되면 즉시 탐색을 중단한다.

    Args:
        target_text (str): 해독할 암호 문자열

    Returns:
        tuple: (발견된 자리수(int 또는 None), 해독된 문자열(str 또는 None))
               사전 단어가 발견된 경우 해당 값 반환, 미발견 시 (None, None)
    """
    # 보너스 과제: 자동 탐지에 사용할 텍스트 사전
    dictionary = [
        'mars', 'love', 'base', 'roman', 'caesar',
        'system', 'secret', 'open', 'door', 'the'
    ]

    print('=' * 50)
    print('  카이사르 암호 해독 시작')
    print('=' * 50)

    # 알파벳 수(26)만큼 자리수를 바꾸며 반복
    for shift in range(26):
        decoded_text = decode_with_shift(target_text, shift)

        # 자리수별 해독 결과를 눈으로 확인할 수 있도록 출력
        print(f'  자리수 [{shift:02d}] : {decoded_text}')

        # 보너스 과제: 사전 단어가 해독 결과에 포함되면 탐색 중단
        lower_decoded = decoded_text.lower()
        for word in dictionary:
            if word in lower_decoded:
                print(
                    f'\n[자동 탐지] 키워드 "{word}" 발견 '
                    f'→ 자리수 {shift}번에서 탐색 중단'
                )
                return shift, decoded_text

    # 26자리를 모두 시도해도 사전 단어 미발견
    return None, None


def main():
    """메인 실행 함수: 암호 파일 읽기 → 해독 → 결과 저장."""
    password_file = 'password.txt'
    result_file = 'result.txt'

    # 1. 암호문 파일 읽기
    target_text = read_password_file(password_file)
    if target_text is None:
        return

    print(f'\n[암호문 로드] "{target_text}"\n')

    # 2. 카이사르 암호 해독 (보너스: 사전 자동 탐지 포함)
    found_shift, decoded_text = caesar_cipher_decode(target_text)

    # 3. 결과 처리 및 result.txt 저장
    if found_shift is not None:
        # 보너스 사전에 의해 정답 자동 발견
        save_result_file(result_file, decoded_text)
    else:
        # 사전 미발견 → 사용자가 직접 자리수 입력
        print('\n[알림] 사전에 일치하는 단어가 없습니다.')
        print('위 출력 결과를 확인하고 올바른 의미의 문장 자리수를 입력하세요.')

        try:
            user_input = input('\n정답 자리수 입력 (0~25): ')
            selected_shift = int(user_input)

            if not 0 <= selected_shift <= 25:
                print('오류: 자리수는 0~25 사이 숫자여야 합니다.')
                return

            final_text = decode_with_shift(target_text, selected_shift)
            save_result_file(result_file, final_text)

        except ValueError:
            print('오류: 숫자를 입력해야 합니다. 프로그램을 종료합니다.')


if __name__ == '__main__':
    main()
