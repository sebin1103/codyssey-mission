def process_mars_inventory():
    file_name = 'Mars_Base_Inventory_List.csv'
    danger_file_name = 'Mars_Base_Inventory_danger.csv'
    bin_file_name = 'Mars_Base_Inventory_List.bin'
    
    inventory_list = [] 
    header = ''
    
    # 1. Mars_Base_Inventory_List.csv 의 내용을 읽어 들어서 출력한다.
    print('--- 원본 파일 내용 출력 ---')
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                header = lines[0].strip()
                print(header)
                
                for line in lines[1:]:
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                        
                    print(clean_line)
                    
                    # 2. Mars_Base_Inventory_List.csv 내용을 읽어서 Python의 리스트(List) 객체로 변환한다.
                    parts = clean_line.split(',')
                    if len(parts) >= 5:
                        substance = parts[0]
                        weight = parts[1]
                        specific_gravity = parts[2]
                        strength = parts[3]
                    
                        
                        try:
                            flammability = float(parts[4])
                        except ValueError:
                            flammability = 0.0
                            
                        inventory_list.append([substance, weight, specific_gravity, strength, flammability])
                        
    except FileNotFoundError:
        print('오류: 파일을 찾을 수 없습니다.')
        return
    except Exception as e:
        print('파일을 읽는 중 오류가 발생했습니다:', e)
        return

    # 3. 배열 내용을 적제 화물 목록을 인화성이 높은 순으로 정렬한다.
    inventory_list.sort(key=lambda x: x[4], reverse=True)

    # 4. 인화성 지수가 0.7 이상되는 목록을 뽑아서 별도로 출력한다.
    danger_list = [item for item in inventory_list if item[4] >= 0.7]
    
    print('\n--- 인화성 지수 0.7 이상 위험 물품 목록 ---')
    for item in danger_list:
        print(f'{item[0]}, {item[1]}, {item[2]}, {item[3]}, {item[4]}')

    # 5. 인화성 지수가 0.7 이상되는 목록을 CSV 포멧(Mars_Base_Inventory_danger.csv)으로 저장한다.
    try:
        with open(danger_file_name, 'w', encoding='utf-8') as f:
            f.write(header + '\n')
            for item in danger_list:
                line_str = f'{item[0]},{item[1]},{item[2]},{item[3]},{item[4]}\n'
                f.write(line_str)
        print(f'\n위험 물품 목록이 {danger_file_name} 파일로 성공적으로 저장되었습니다.')
    except Exception as e:
        print('CSV 파일을 저장하는 중 오류가 발생했습니다:', e)

    # 6. 인화성 순서로 정렬된 배열의 내용을 이진 파일형태로 저장한다. 파일이름은 Mars_Base_Inventory_List.bin [보너스 과제]
    try:
        with open(bin_file_name, 'wb') as f:
            for item in inventory_list:
                line_str = f'{item[0]},{item[1]},{item[2]},{item[3]},{item[4]}\n'
                # 문자열을 바이트 객체로 인코딩하여 이진 파일에 쓰기
                f.write(line_str.encode('utf-8'))
        print(f'정렬된 목록이 {bin_file_name} 파일로 성공적으로 저장되었습니다.')
    except Exception as e:
        print('이진 파일을 저장하는 중 오류가 발생했습니다:', e)

    # 7. 저장된 Mars_Base_Inventory_List.bin 의 내용을 다시 읽어 들여서 화면에 내용을 출력한다. [보너스 과제]
    print('\n--- 이진 파일에서 읽어 들인 내용 ---')
    try:
        with open(bin_file_name, 'rb') as f:
            binary_content = f.read()
            print(binary_content.decode('utf-8').strip())
    except Exception as e:
        print('이진 파일을 읽는 중 오류가 발생했습니다:', e)

# 메인 함수 실행
if __name__ == '__main__':
    process_mars_inventory()