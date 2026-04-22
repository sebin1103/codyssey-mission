import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit
from PyQt5.QtCore import Qt

class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        self.current_text = ''
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Survival Calculator')

        main_layout = QVBoxLayout()

        self.display = QLineEdit('0')
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True)
        self.display.setStyleSheet('font-size: 30px; padding: 10px;')
        main_layout.addWidget(self.display)
      
        grid_layout = QGridLayout()
        
        buttons = [
            ['AC', '+/-', '%', '/'],
            ['7', '8', '9', '*'],
            ['4', '5', '6', '-'],
            ['1', '2', '3', '+']
        ]
      
        for row, row_buttons in enumerate(buttons):
            for col, button_text in enumerate(row_buttons):
                button = QPushButton(button_text)
                button.setFixedSize(60, 60)
                button.clicked.connect(self.button_clicked)
                grid_layout.addWidget(button, row, col)
     
        btn_0 = QPushButton('0')
        btn_0.setFixedSize(125, 60)
        btn_0.clicked.connect(self.button_clicked)
        grid_layout.addWidget(btn_0, 4, 0, 1, 2)
        
        btn_dot = QPushButton('.')
        btn_dot.setFixedSize(60, 60)
        btn_dot.clicked.connect(self.button_clicked)
        grid_layout.addWidget(btn_dot, 4, 2)
        
        btn_eq = QPushButton('=')
        btn_eq.setFixedSize(60, 60)
        btn_eq.clicked.connect(self.button_clicked)
        grid_layout.addWidget(btn_eq, 4, 3)

        main_layout.addLayout(grid_layout)
        self.setLayout(main_layout)
        self.show()

    def button_clicked(self):
        sender = self.sender()
        text = sender.text()

        if text == 'AC':
            self.current_text = ''
            self.display.setText('0')
        elif text == '=':
            try:
                result = str(eval(self.current_text))
                self.display.setText(result)
                self.current_text = result
            except Exception:
                self.display.setText('Error')
                self.current_text = ''
        elif text == '+/-':
            if self.current_text:
                if self.current_text.startswith('-'):
                    self.current_text = self.current_text[1:]
                else:
                    self.current_text = '-' + self.current_text
                self.display.setText(self.current_text)
        elif text == '%':
            try:
                result = str(eval(self.current_text) / 100)
                self.display.setText(result)
                self.current_text = result
            except Exception:
                self.display.setText('Error')
                self.current_text = ''
        else:
            self.current_text += text
            self.display.setText(self.current_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    calc = Calculator()
    sys.exit(app.exec_())