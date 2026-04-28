import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Calculator:
    """계산기의 핵심 연산을 담당하는 클래스."""

    # 처리 가능한 숫자 범위 한계 (float 최대값 근방)
    MAX_VALUE = 1e308
    # 소수점 반올림 자릿수 (보너스 과제)
    DECIMAL_PLACES = 6

    def __init__(self):
        self.reset()

    # ------------------------------------------------------------------
    # 상태 제어
    # ------------------------------------------------------------------
    def reset(self):
        """모든 상태를 초기화한다."""
        self.current = '0'
        self.previous = None
        self.operator = None
        # True 이면 다음 숫자 입력 시 화면을 새로 시작한다.
        self.start_new = False

    def negative_positive(self):
        """현재 표시 값의 부호를 토글한다."""
        if self.current in ('Error', 'Overflow'):
            return self.current
        if self.current.startswith('-'):
            self.current = self.current[1:]
        elif self.current != '0':
            self.current = '-' + self.current
        return self.current

    def percent(self):
        """현재 표시 값을 100으로 나눈다."""
        if self.current in ('Error', 'Overflow'):
            return self.current
        try:
            value = float(self.current) / 100
            self.current = self._format_number(value)
        except (ValueError, OverflowError):
            self.current = 'Error'
        return self.current

    # ------------------------------------------------------------------
    # 사칙 연산
    # ------------------------------------------------------------------
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError('0으로 나눌 수 없습니다')
        return a / b

    # ------------------------------------------------------------------
    # 입력 처리
    # ------------------------------------------------------------------
    def input_digit(self, digit):
        """숫자 키 입력. 누를 때마다 화면에 누적한다."""
        if self.current in ('Error', 'Overflow'):
            self.reset()
        if self.start_new:
            self.current = '0'
            self.start_new = False
        if self.current == '0':
            self.current = digit
        elif self.current == '-0':
            self.current = '-' + digit
        else:
            # 너무 길어지는 입력 차단 (한 줄에 표시 가능한 길이로 제한)
            if len(self.current.lstrip('-').replace('.', '')) >= 16:
                return self.current
            self.current += digit
        return self.current

    def input_dot(self):
        """소수점 입력. 이미 있으면 무시한다."""
        if self.current in ('Error', 'Overflow'):
            self.reset()
        if self.start_new:
            self.current = '0'
            self.start_new = False
        if '.' not in self.current:
            self.current += '.'
        return self.current

    def set_operator(self, op):
        """연산자 키 입력."""
        if self.current in ('Error', 'Overflow'):
            return self.current
        # 직전 입력이 숫자였다면, 누적된 연산을 먼저 처리한다.
        if (
            self.previous is not None
            and self.operator is not None
            and not self.start_new
        ):
            self.equal()
            if self.current in ('Error', 'Overflow'):
                return self.current
        try:
            self.previous = float(self.current)
        except ValueError:
            self.current = 'Error'
            return self.current
        self.operator = op
        self.start_new = True
        return self.current

    def equal(self):
        """= 키. 누적된 연산 결과를 계산해 화면에 표시한다."""
        if self.current in ('Error', 'Overflow'):
            return self.current
        if self.previous is None or self.operator is None:
            return self.current
        try:
            a = self.previous
            b = float(self.current)
            if self.operator == '+':
                result = self.add(a, b)
            elif self.operator == '-':
                result = self.subtract(a, b)
            elif self.operator == '*':
                result = self.multiply(a, b)
            elif self.operator == '/':
                result = self.divide(a, b)
            else:
                return self.current

            # 오버플로우 / NaN 검사
            if result != result or result == float('inf') or result == float('-inf'):
                raise OverflowError('처리 가능한 범위를 초과했습니다')
            if abs(result) > self.MAX_VALUE:
                raise OverflowError('처리 가능한 범위를 초과했습니다')

            self.current = self._format_number(result)
        except ZeroDivisionError:
            self.current = 'Error'
        except OverflowError:
            self.current = 'Overflow'
        except Exception:
            self.current = 'Error'

        self.previous = None
        self.operator = None
        self.start_new = True
        return self.current

    # ------------------------------------------------------------------
    # 헬퍼
    # ------------------------------------------------------------------
    @classmethod
    def _format_number(cls, value):
        """소수점 6자리 이하 반올림 후 문자열로 변환한다."""
        if value != value or value == float('inf') or value == float('-inf'):
            raise OverflowError
        rounded = round(value, cls.DECIMAL_PLACES)
        # 정수면 정수 표기
        if rounded == int(rounded) and abs(rounded) < 1e16:
            return str(int(rounded))
        # 불필요한 0 제거
        text = f'{rounded:.{cls.DECIMAL_PLACES}f}'.rstrip('0').rstrip('.')
        return text if text else '0'


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
class CalculatorUI(QWidget):
    """아이폰 스타일 계산기 UI."""

    # 버튼 정의: (텍스트, row, col, row_span, col_span, 카테고리)
    BUTTONS = (
        ('AC', 1, 0, 1, 1, 'function'),
        ('+/-', 1, 1, 1, 1, 'function'),
        ('%', 1, 2, 1, 1, 'function'),
        ('/', 1, 3, 1, 1, 'operator'),
        ('7', 2, 0, 1, 1, 'digit'),
        ('8', 2, 1, 1, 1, 'digit'),
        ('9', 2, 2, 1, 1, 'digit'),
        ('*', 2, 3, 1, 1, 'operator'),
        ('4', 3, 0, 1, 1, 'digit'),
        ('5', 3, 1, 1, 1, 'digit'),
        ('6', 3, 2, 1, 1, 'digit'),
        ('-', 3, 3, 1, 1, 'operator'),
        ('1', 4, 0, 1, 1, 'digit'),
        ('2', 4, 1, 1, 1, 'digit'),
        ('3', 4, 2, 1, 1, 'digit'),
        ('+', 4, 3, 1, 1, 'operator'),
        ('0', 5, 0, 1, 2, 'digit'),
        ('.', 5, 2, 1, 1, 'digit'),
        ('=', 5, 3, 1, 1, 'operator'),
    )

    STYLE_DIGIT = (
        'QPushButton {'
        '  background-color: #333333; color: white;'
        '  border: none; border-radius: 35px; font-size: 24px;'
        '}'
        'QPushButton:pressed { background-color: #555555; }'
    )
    STYLE_FUNCTION = (
        'QPushButton {'
        '  background-color: #a5a5a5; color: black;'
        '  border: none; border-radius: 35px; font-size: 22px;'
        '}'
        'QPushButton:pressed { background-color: #d4d4d2; }'
    )
    STYLE_OPERATOR = (
        'QPushButton {'
        '  background-color: #ff9500; color: white;'
        '  border: none; border-radius: 35px; font-size: 28px;'
        '}'
        'QPushButton:pressed { background-color: #ffb143; }'
    )

    def __init__(self):
        super().__init__()
        self.calc = Calculator()
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle('계산기')
        self.setStyleSheet('background-color: black;')
        self.setFixedSize(320, 500)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # 디스플레이
        self.display = QLabel('0')
        self.display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.display.setStyleSheet('color: white; padding-right: 10px;')
        self._base_font_size = 56
        self.display.setFont(QFont('Helvetica', self._base_font_size))
        self.display.setMinimumHeight(90)
        main_layout.addWidget(self.display)

        # 버튼 그리드
        grid = QGridLayout()
        grid.setSpacing(8)

        for text, row, col, rs, cs, kind in self.BUTTONS:
            btn = QPushButton(text)
            btn.setFixedHeight(70)
            if cs == 1:
                btn.setFixedWidth(70)
            else:
                btn.setMinimumWidth(70 * cs + 8)
            if kind == 'digit':
                btn.setStyleSheet(self.STYLE_DIGIT)
            elif kind == 'function':
                btn.setStyleSheet(self.STYLE_FUNCTION)
            else:
                btn.setStyleSheet(self.STYLE_OPERATOR)
            btn.clicked.connect(lambda _checked, t=text: self._on_click(t))
            grid.addWidget(btn, row, col, rs, cs)

        main_layout.addLayout(grid)
        self.setLayout(main_layout)

    # ------------------------------------------------------------------
    # 이벤트
    # ------------------------------------------------------------------
    def _on_click(self, text):
        if text.isdigit():
            self.calc.input_digit(text)
        elif text == '.':
            self.calc.input_dot()
        elif text == 'AC':
            self.calc.reset()
        elif text == '+/-':
            self.calc.negative_positive()
        elif text == '%':
            self.calc.percent()
        elif text in ('+', '-', '*', '/'):
            self.calc.set_operator(text)
        elif text == '=':
            self.calc.equal()
        self._update_display()

    def _update_display(self):
        text = self.calc.current
        self.display.setText(text)
        self._adjust_font_size(text)

    def _adjust_font_size(self, text):
        """보너스 과제: 길이에 따라 폰트 크기를 조정한다."""
        length = len(text)
        if length <= 7:
            size = self._base_font_size
        elif length <= 9:
            size = 46
        elif length <= 12:
            size = 36
        elif length <= 16:
            size = 28
        else:
            size = 22
        self.display.setFont(QFont('Helvetica', size))


def main():
    app = QApplication(sys.argv)
    window = CalculatorUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
