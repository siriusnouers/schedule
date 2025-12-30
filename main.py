import sys
import re
import json
import os
import winreg 
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QLineEdit, QCalendarWidget, QListWidget, 
                               QListWidgetItem, QFrame, QCheckBox, QSystemTrayIcon, QMenu, 
                               QDialog, QFileDialog, QMessageBox, QTabWidget, QComboBox, QGroupBox,
                               QGraphicsDropShadowEffect, QSlider)
from PySide6.QtCore import Qt, QDate, QPoint, QRect, QSharedMemory, QSettings, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTextCharFormat, QAction, QPixmap, QIcon, QFont

# --- 1. 全局常量 ---
DATA_FILE = "todo_data.json" 
NO_DATE_KEY = "no_date_tasks"
ICON_FILE = "icon.ico"
APP_ID = "MyDesktopTodo_Unique_ID_v23" 
ORG_NAME = "MySoft"
APP_NAME = "DesktopTodo"

# --- 2. 主题配置 ---
THEMES = [
    {
        "name": "极简白",
        "base_rgb": "255, 255, 255", 
        "text_main": "#2d3436", "text_done": "#b2bec3", "accent": "#6c5ce7", 
        "input_bg": "rgba(241, 242, 246, 0.8)",
        "cal_bg": "#ffffff", "cal_text": "#2d3436", "cal_sel_bg": "#6c5ce7", "cal_sel_txt": "white",
        "btn_hover": "rgba(108, 92, 231, 0.1)", "close_hover": "#ff7675",
        "checkbox_border": "#dfe6e9", "circle": "#ff7675",
        "card_bg": "#ffffff"
    },
    {
        "name": "暗夜蓝",
        "base_rgb": "45, 52, 54",
        "text_main": "#dfe6e9", "text_done": "#636e72", "accent": "#0984e3", 
        "input_bg": "rgba(99, 110, 114, 0.3)",
        "cal_bg": "#2d3436", "cal_text": "#dfe6e9", "cal_sel_bg": "#0984e3", "cal_sel_txt": "white",
        "btn_hover": "rgba(9, 132, 227, 0.2)", "close_hover": "#d63031",
        "checkbox_border": "#636e72", "circle": "#fab1a0",
        "card_bg": "#353b48"
    },
    {
        "name": "莫兰迪",
        "base_rgb": "235, 237, 241",
        "text_main": "#57606f", "text_done": "#a4b0be", "accent": "#ffa502", 
        "input_bg": "rgba(255, 255, 255, 0.6)",
        "cal_bg": "#f1f2f6", "cal_text": "#2f3542", "cal_sel_bg": "#ffa502", "cal_sel_txt": "white",
        "btn_hover": "rgba(255, 165, 2, 0.1)", "close_hover": "#ff4757",
        "checkbox_border": "#ced4da", "circle": "#ff6b81",
        "card_bg": "#ffffff"
    }
]

# --- 3. 组件 ---
class TaskItemWidget(QWidget):
    def __init__(self, task_data, theme, on_status_change, on_delete, on_edit_request, on_data_changed):
        super().__init__()
        self.task_data = task_data
        self.theme = theme
        self.on_delete = on_delete
        self.on_edit_request = on_edit_request
        self.on_data_changed = on_data_changed

        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 4, 8, 4)
        self.main_layout.setSpacing(0)

        # 卡片容器
        self.card = QFrame()
        self.card.setObjectName("TaskCard")
        self.card_layout = QHBoxLayout(self.card)
        self.card_layout.setContentsMargins(12, 10, 12, 10)
        self.card_layout.setSpacing(12)
        
        # 优先级指示条 (圆角)
        self.priority_bar = QFrame()
        self.priority_bar.setFixedWidth(5)
        self.priority_bar.setStyleSheet(self.get_priority_style(task_data.get("priority", 0)))
        self.card_layout.addWidget(self.priority_bar)

        # 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(task_data.get("done", False))
        self.checkbox.stateChanged.connect(on_status_change)
        self.checkbox.setFixedSize(22, 22)
        self.checkbox.setCursor(Qt.PointingHandCursor)

        # 内容容器
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)

        # 时间显示 (带图标)
        time_text = task_data.get("time", "")
        self.time_label = QLabel(f"🕒 {time_text}" if time_text else "")
        self.time_label.setStyleSheet(f"color: {theme['accent']}; font-size: 9pt; font-weight: bold;")
        if not time_text: self.time_label.hide()
        content_layout.addWidget(self.time_label)

        self.label = QLabel(task_data.get("text", ""))
        self.label.setWordWrap(True)
        f = QFont("Microsoft YaHei", 11)
        if not task_data.get("done", False): f.setWeight(QFont.Medium)
        self.label.setFont(f)
        content_layout.addWidget(self.label)
        
        self.card_layout.addWidget(self.checkbox)
        self.card_layout.addLayout(content_layout, 1)

        # 删除按钮 (悬停显示)
        self.del_btn = QPushButton("🗑️")
        self.del_btn.setFixedSize(28, 28)
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.clicked.connect(on_delete)
        self.del_btn.setStyleSheet(f"background: transparent; color: {theme['text_done']}; border: none; font-size: 14px;")
        self.del_btn.hide()
        self.card_layout.addWidget(self.del_btn)

        self.main_layout.addWidget(self.card)
        self.update_style(task_data.get("done", False))
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def get_priority_style(self, p):
        colors = {0: "transparent", 1: "#a4b0be", 2: "#ffa502", 3: "#ff4757"}
        return f"background-color: {colors.get(p, 'transparent')}; border-radius: 2px;"

    def enterEvent(self, event):
        self.del_btn.show()
        self.card.setStyleSheet(f"background-color: {self.theme['card_bg']}; border: 1.5px solid {self.theme['accent']}; border-radius: 10px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.del_btn.hide()
        self.card.setStyleSheet(f"background-color: {self.theme['card_bg']}; border: 1px solid rgba(0,0,0,0.15); border-radius: 10px;")
        super().leaveEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"background-color: white; color: #2d3436; border-radius: 8px; padding: 5px;")
        
        edit_act = QAction("✏️ 编辑任务", self)
        edit_act.triggered.connect(self.on_edit_request)
        
        del_act = QAction("🗑️ 删除任务", self)
        del_act.triggered.connect(self.on_delete)
        
        p_menu = menu.addMenu("🚩 设置优先级")
        priorities = [("⚪ 无", 0), ("🔵 低", 1), ("🟡 中", 2), ("🔴 高", 3)]
        for name, val in priorities:
            act = QAction(name, self)
            act.triggered.connect(lambda checked=False, p=val: self.on_edit_priority(p))
            p_menu.addAction(act)

        menu.addSeparator()
        menu.addAction(edit_act)
        menu.addAction(del_act)
        menu.exec(self.mapToGlobal(pos))

    def on_edit_priority(self, p):
        self.task_data["priority"] = p
        self.priority_bar.setStyleSheet(self.get_priority_style(p))
        self.on_data_changed()

    def update_style(self, is_done):
        self.card.setStyleSheet(f"background-color: {self.theme['card_bg']}; border: 1px solid rgba(0,0,0,0.15); border-radius: 10px;")
        
        font = self.label.font()
        font.setStrikeOut(is_done)
        self.label.setFont(font)
        
        color = self.theme["text_done"] if is_done else self.theme["text_main"]
        self.label.setStyleSheet(f"color: {color}; border: none; background: transparent;")
        
        chk_style = f"""
            QCheckBox::indicator {{
                width: 20px; height: 20px;
                border: 2px solid {self.theme['checkbox_border']};
                border-radius: 11px; background: transparent;
            }}
            QCheckBox::indicator:hover {{ border-color: {self.theme['accent']}; }}
            QCheckBox::indicator:checked {{
                background-color: {self.theme['accent']};
                border-color: {self.theme['accent']};
            }}
        """
        self.checkbox.setStyleSheet(chk_style)

class CircleCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.marked_dates = set()
        self.theme = THEMES[0]
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames) 
        self.setNavigationBarVisible(True)
        self.setSelectionMode(QCalendarWidget.SingleSelection)

    def update_theme(self, theme):
        self.theme = theme
        fmt = QTextCharFormat()
        fmt.setForeground(QBrush(QColor(theme["cal_text"])))
        self.setWeekdayTextFormat(Qt.Saturday, fmt)
        self.setWeekdayTextFormat(Qt.Sunday, fmt)
        self.update()

    def set_markers(self, dates):
        self.marked_dates = dates
        self.update() 

    def paintCell(self, painter, rect, date):
        try:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 1. 背景
            painter.setPen(Qt.NoPen)
            if "cal_bg" in self.theme:
                painter.setBrush(QColor(self.theme["cal_bg"]))
            else:
                painter.setBrush(QColor("white"))
            painter.drawRect(rect)

            is_selected = (date == self.selectedDate())
            is_today = (date == QDate.currentDate())
            has_task = (date.toString("yyyy-MM-dd") in self.marked_dates)
            
            # 2. 今天 (底色)
            if is_today:
                accent = self.theme.get("accent", "#6c5ce7")
                c = QColor(accent)
                c.setAlpha(50) 
                painter.setBrush(c)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 8, 8)

            # 3. 选中 (圆圈)
            if is_selected:
                bg = self.theme.get("cal_sel_bg", "#6c5ce7")
                painter.setBrush(QColor(bg))
                painter.setPen(Qt.NoPen)
                size = min(rect.width(), rect.height()) - 12
                painter.drawEllipse(rect.center(), size/2, size/2)
            
            # 4. 待办 (点)
            if has_task:
                if is_selected:
                    dot_color = QColor("white")
                else:
                    dot_color = QColor(self.theme.get("circle", "red"))
                painter.setBrush(dot_color)
                painter.setPen(Qt.NoPen)
                center = rect.bottomCenter()
                painter.drawEllipse(QPoint(center.x(), center.y() - 6), 2.5, 2.5)

            # 5. 文字
            if is_selected:
                text_color = QColor(self.theme.get("cal_sel_txt", "white"))
            elif is_today:
                text_color = QColor(self.theme.get("accent", "blue"))
            elif date.month() != self.monthShown():
                text_color = QColor(self.theme.get("text_done", "gray"))
            else:
                text_color = QColor(self.theme.get("cal_text", "black"))
                
            painter.setPen(QPen(text_color, 1)) 
            
            f = self.font()
            if is_today or is_selected: f.setBold(True)
            painter.setFont(f)
            
            painter.drawText(rect, Qt.AlignCenter, str(date.day()))
            
        except Exception as e:
            print(f"Paint error: {e}")
            painter.setPen(Qt.black)
            painter.drawText(rect, Qt.AlignCenter, str(date.day()))
        finally:
            painter.restore()

# --- 4. 设置中心 (简约版) ---
class SettingsDialog(QDialog):
    def __init__(self, theme, settings, current_path, callbacks):
        super().__init__()
        self.setWindowTitle("设置")
        self.resize(380, 250)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.theme = theme
        self.settings = settings
        self.current_path = current_path
        self.callbacks = callbacks
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.bg = QFrame()
        self.update_dialog_style() 
        bg_layout = QVBoxLayout(self.bg)
        layout.addWidget(self.bg)

        # 标题
        title_layout = QHBoxLayout()
        lbl_title = QLabel("⚙️ 设置")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        btn_close = QPushButton("×")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"border:none; font-size:18px; color:{self.theme['text_main']};")
        title_layout.addWidget(lbl_title)
        title_layout.addStretch()
        title_layout.addWidget(btn_close)
        bg_layout.addLayout(title_layout)

        tabs = QTabWidget()
        bg_layout.addWidget(tabs)

        # Tab 1: 常规
        tab_general = QWidget()
        layout_gen = QVBoxLayout(tab_general)
        
        self.cb_autostart = QCheckBox("开机自动启动")
        self.cb_autostart.setChecked(self.settings.get("auto_start", False))
        self.cb_autostart.stateChanged.connect(lambda s: self.callbacks['update_autostart'](s==2))
        layout_gen.addWidget(self.cb_autostart)

        self.cb_ontop = QCheckBox("窗口置顶 (始终显示在最前)")
        self.cb_ontop.setChecked(self.settings.get("always_on_top", False))
        self.cb_ontop.stateChanged.connect(lambda s: self.callbacks['update_ontop'](s==2))
        layout_gen.addWidget(self.cb_ontop)

        layout_gen.addWidget(QLabel("界面透明度:"))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(50, 255)
        self.slider_opacity.setValue(self.settings.get("opacity", 240))
        self.slider_opacity.valueChanged.connect(self.callbacks['update_opacity'])
        layout_gen.addWidget(self.slider_opacity)

        group_close = QGroupBox("关闭按钮 (×) 行为")
        layout_close = QVBoxLayout(group_close)
        self.combo_close = QComboBox()
        self.combo_close.addItems(["每次询问 (默认)", "最小化到托盘", "彻底退出程序"])
        idx = {"minimize": 1, "quit": 2}.get(self.settings.get("close_action", "ask"), 0)
        self.combo_close.setCurrentIndex(idx)
        self.combo_close.currentIndexChanged.connect(self.on_close_action_change)
        layout_close.addWidget(self.combo_close)
        layout_gen.addWidget(group_close)
        layout_gen.addStretch()
        tabs.addTab(tab_general, "常规")

        # Tab 2: 数据
        tab_data = QWidget()
        layout_data = QVBoxLayout(tab_data)
        layout_data.addWidget(QLabel("数据位置:"))
        self.input_path = QLineEdit(self.current_path)
        self.input_path.setReadOnly(True)
        self.input_path.setStyleSheet(f"background:rgba(0,0,0,10); border:1px solid #ccc; padding:5px; border-radius:4px; color:{self.theme['text_main']}")
        layout_data.addWidget(self.input_path)
        btn_change = QPushButton("📂 迁移数据位置")
        btn_change.setStyleSheet(f"background:{self.theme['accent']}; color:white; padding:6px; border-radius:4px;")
        btn_change.clicked.connect(self.on_change_path)
        layout_data.addWidget(btn_change)
        layout_data.addStretch()
        tabs.addTab(tab_data, "数据")

    def update_dialog_style(self):
        self.bg.setStyleSheet(f"""
            QFrame {{ 
                background-color: {self.theme['cal_bg']}; 
                border: 1px solid rgba(0,0,0,0.1); 
                border-radius: 15px; 
            }}
            QLabel, QCheckBox {{ color: {self.theme['text_main']}; font-size: 10pt; }}
            QGroupBox {{ 
                border: 1px solid rgba(0,0,0,0.05); 
                border-radius: 10px; 
                margin-top: 15px; 
                padding-top: 20px; 
                font-weight: bold; 
                color: {self.theme['accent']}; 
            }}
            QTabWidget::pane {{ border: 0; }}
            QTabBar::tab {{ 
                background: transparent; 
                padding: 10px 20px; 
                color: {self.theme['text_main']}; 
                font-weight: bold;
            }}
            QTabBar::tab:selected {{ 
                border-bottom: 3px solid {self.theme['accent']}; 
                color: {self.theme['accent']}; 
            }}
            QComboBox {{ 
                border: 1px solid rgba(0,0,0,0.1); 
                padding: 6px; 
                border-radius: 6px; 
                color: {self.theme['text_main']}; 
                background: {self.theme['input_bg']}; 
            }}
        """)

    def on_close_action_change(self, index):
        self.settings["close_action"] = ["ask", "minimize", "quit"][index]
        self.callbacks['save_settings']()
    def on_change_path(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            new_path = os.path.join(folder, DATA_FILE)
            if new_path != self.current_path:
                self.input_path.setText(new_path)
                self.callbacks['update_path'](new_path)

# --- 5. 关闭询问对话框 ---
class EditTaskDialog(QDialog):
    def __init__(self, theme, text, time):
        super().__init__()
        self.setWindowTitle("编辑任务")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.theme = theme
        self.init_ui(text, time)
    def init_ui(self, text, time):
        layout = QVBoxLayout()
        self.setLayout(layout)
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {self.theme['cal_bg']}; 
            border: 1px solid rgba(0,0,0,0.1); 
            border-radius: 15px;
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(15)
        layout.addWidget(frame)
        
        title = QLabel("✏️ 编辑任务")
        title.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {self.theme['accent']};")
        frame_layout.addWidget(title)

        frame_layout.addWidget(QLabel("任务内容:"))
        self.edit_text = QLineEdit(text)
        self.edit_text.setStyleSheet(f"background: {self.theme['input_bg']}; border-radius: 8px; padding: 8px;")
        frame_layout.addWidget(self.edit_text)
        
        frame_layout.addWidget(QLabel("时间 (可选, 如 14:30):"))
        self.edit_time = QLineEdit(time)
        self.edit_time.setStyleSheet(f"background: {self.theme['input_bg']}; border-radius: 8px; padding: 8px;")
        frame_layout.addWidget(self.edit_time)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"background: transparent; color: {self.theme['text_done']}; border: 1px solid {self.theme['text_done']};")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        frame_layout.addLayout(btn_layout)

class CloseOptionDialog(QDialog):
    def __init__(self, theme):
        super().__init__()
        self.setWindowTitle("关闭选项")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.theme = theme
        self.result_action = None
        self.remember = False
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {self.theme['cal_bg']}; border: 1px solid rgba(0,0,0,0.1); border-radius: 15px;")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(frame)
        
        lbl = QLabel("👋 准备离开了吗？")
        lbl.setStyleSheet(f"color: {self.theme['text_main']}; font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        frame_layout.addWidget(lbl)
        
        btn_layout = QHBoxLayout()
        self.btn_tray = QPushButton("最小化到托盘")
        self.btn_tray.setCursor(Qt.PointingHandCursor)
        self.btn_tray.setStyleSheet(f"background-color: {self.theme['accent']}; color: white; padding: 10px; border-radius: 8px;")
        self.btn_tray.clicked.connect(lambda: self.done_with('minimize'))
        
        self.btn_quit = QPushButton("彻底退出")
        self.btn_quit.setCursor(Qt.PointingHandCursor)
        self.btn_quit.setStyleSheet(f"background-color: transparent; color: {self.theme['close_hover']}; border: 1px solid {self.theme['close_hover']}; padding: 10px; border-radius: 8px;")
        self.btn_quit.clicked.connect(lambda: self.done_with('quit'))
        
        btn_layout.addWidget(self.btn_tray)
        btn_layout.addWidget(self.btn_quit)
        frame_layout.addLayout(btn_layout)
        
        self.cb_remember = QCheckBox("记住我的选择，不再提示")
        self.cb_remember.setStyleSheet(f"color: {self.theme['text_done']}; margin-top: 10px; font-size: 9pt;")
        frame_layout.addWidget(self.cb_remember)
    def done_with(self, action):
        self.result_action = action
        self.remember = self.cb_remember.isChecked()
        self.accept()

# --- 6. 主程序 ---
class DesktopWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Todo V23")
        self.resize(340, 600)
        
        self.app_settings = QSettings(ORG_NAME, APP_NAME)
        self.tasks = {}
        self.settings = {"close_action": "ask", "auto_start": False, "opacity": 240, "always_on_top": False}
        self.current_theme_idx = 0 
        self.current_selected_date = QDate.currentDate()
        self.notified_tasks = set() # 记录今天已提醒的任务
        
        self.data_file_path = self.get_data_file_path()
        self.load_data() 
        
        # 初始化窗口标志
        self.update_window_flags()
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.drag_pos = None
        self.resize_margin = 8
        self.resizing = False
        self.resize_edge = None

        self.init_ui()
        self.apply_theme() 
        self.refresh_all_lists()
        self.setMouseTracking(True)
        self.left_container.setMouseTracking(True)
        self.check_auto_start_state()
        self.init_system_tray()

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(30000) # 每30秒检查一次

    def check_reminders(self):
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        
        if today_str in self.tasks:
            for task in self.tasks[today_str]:
                if not task.get('done') and task.get('time') == current_time:
                    task_id = f"{today_str}_{task['text']}_{current_time}"
                    if task_id not in self.notified_tasks:
                        self.tray_icon.showMessage("任务提醒", f"⏰ {current_time}: {task['text']}", QSystemTrayIcon.Information, 5000)
                        self.notified_tasks.add(task_id)

    def init_ui(self):
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)
        self.setLayout(self.main_layout)

        self.left_container = QFrame()
        self.left_container.setMinimumWidth(300) 
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(10, 10, 10, 10)
        
        top_bar = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("💡 1209 14:30 去医院 !3")
        self.input_box.returnPressed.connect(self.handle_smart_add)
        top_bar.addWidget(self.input_box, 1)
        self.btn_min = QPushButton("—")
        self.btn_min.setFixedSize(30, 30)
        self.btn_min.setCursor(Qt.PointingHandCursor)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.handle_close_request)
        top_bar.addWidget(self.btn_min)
        top_bar.addWidget(self.btn_close)
        self.left_layout.addLayout(top_bar)

        # 搜索栏
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索任务...")
        self.search_box.textChanged.connect(lambda: self.refresh_all_lists())
        self.search_box.setStyleSheet("height: 25px; font-size: 10pt;")
        self.left_layout.addWidget(self.search_box)

        header = QHBoxLayout()
        self.title_label = QLabel("📋 全部待办")
        
        self.theme_btn = QPushButton("🎨")
        self.theme_btn.setFixedWidth(40)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.switch_theme)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedWidth(40)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self.open_settings_dialog)

        self.toggle_btn = QPushButton("日历 [≡]")
        self.toggle_btn.setFixedWidth(70)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_right_panel)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.theme_btn)
        header.addWidget(self.settings_btn)
        header.addWidget(self.toggle_btn)
        self.left_layout.addLayout(header)

        self.left_list = QListWidget()
        self.left_layout.addWidget(self.left_list)
        
        bottom_bar = QHBoxLayout()
        self.show_done_cb = QCheckBox("显示已完成")
        self.show_done_cb.stateChanged.connect(lambda: self.refresh_all_lists())
        bottom_bar.addWidget(self.show_done_cb)
        
        self.clear_done_btn = QPushButton("清理已完成")
        self.clear_done_btn.setFixedWidth(100)
        self.clear_done_btn.setStyleSheet("font-size: 9pt; background-color: transparent; color: gray; border: 1px solid gray;")
        self.clear_done_btn.clicked.connect(self.clear_completed_tasks)
        bottom_bar.addWidget(self.clear_done_btn)
        
        self.left_layout.addLayout(bottom_bar)
        self.main_layout.addWidget(self.left_container)

        self.right_container = QFrame()
        self.right_container.setFixedWidth(280) 
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(10, 10, 10, 10)
        self.calendar = CircleCalendarWidget()
        self.calendar.clicked.connect(self.on_date_selected)
        self.right_layout.addWidget(self.calendar)
        self.sep_line = QFrame()
        self.sep_line.setFrameShape(QFrame.HLine)
        self.right_layout.addWidget(self.sep_line)
        self.selected_date_label = QLabel(f"📅 {self.current_selected_date.toString('M月d日')}")
        self.right_layout.addWidget(self.selected_date_label)
        self.right_list = QListWidget()
        self.right_layout.addWidget(self.right_list)
        self.right_input = QLineEdit()
        self.right_input.setPlaceholderText("添加任务到这一天...")
        self.right_input.returnPressed.connect(self.handle_right_add)
        self.right_layout.addWidget(self.right_input)
        self.right_container.setVisible(False)
        self.main_layout.addWidget(self.right_container)

    def open_settings_dialog(self):
        callbacks = {
            'update_path': self.change_data_path,
            'update_autostart': self.set_auto_start,
            'update_opacity': self.update_opacity,
            'update_ontop': self.update_ontop,
            'save_settings': self.save_data
        }
        dialog = SettingsDialog(THEMES[self.current_theme_idx], self.settings, self.data_file_path, callbacks)
        dialog.move(self.geometry().center() - dialog.rect().center())
        dialog.exec()

    def update_opacity(self, val):
        self.settings["opacity"] = val
        self.apply_theme()
        self.save_data()

    def update_ontop(self, enable):
        self.settings["always_on_top"] = enable
        self.update_window_flags()
        self.save_data()

    def update_window_flags(self):
        # 核心：使用 Qt.Tool 可以避免在 Win+D 时被最小化
        # 使用 Qt.WindowStaysOnTopHint 实现置顶
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.settings.get("always_on_top", False):
            flags |= Qt.WindowStaysOnTopHint
        
        # 重新设置 flags 会导致窗口隐藏，需要重新 show
        pos = self.pos()
        self.setWindowFlags(flags)
        self.move(pos)
        self.show()

    def get_data_file_path(self):
        saved_path = self.app_settings.value("DataPath", None)
        if saved_path and isinstance(saved_path, str): return saved_path
        default_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(default_dir, DATA_FILE)

    def change_data_path(self, new_path):
        self.app_settings.setValue("DataPath", new_path)
        self.data_file_path = new_path
        self.save_data()
        QMessageBox.information(self, "成功", f"数据文件已切换至：\n{new_path}")

    def set_auto_start(self, enable):
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "DesktopTodoApp"
        exe_path = os.path.abspath(sys.argv[0]) 
        try:
            reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key_handle = winreg.OpenKey(reg, key, 0, winreg.KEY_ALL_ACCESS)
            if enable: winreg.SetValueEx(key_handle, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try: winreg.DeleteValue(key_handle, app_name)
                except FileNotFoundError: pass
            winreg.CloseKey(key_handle)
            self.settings["auto_start"] = enable
            self.save_data()
        except Exception as e: print(f"注册表错误: {e}")

    def check_auto_start_state(self):
        if self.settings.get("auto_start", False): self.set_auto_start(True)

    def switch_theme(self):
        self.current_theme_idx = (self.current_theme_idx + 1) % len(THEMES)
        self.apply_theme()
        self.refresh_all_lists()

    def apply_theme(self):
        t = THEMES[self.current_theme_idx]
        self.calendar.update_theme(t)
        
        opacity = self.settings.get("opacity", 240)
        rgba_bg = f"rgba({t['base_rgb']}, {opacity})"
        
        style = f"""
            QWidget {{ font-family: "Microsoft YaHei"; }}
            QFrame#LeftContainer, QFrame#RightContainer {{ 
                background-color: {rgba_bg}; 
                border: 1px solid rgba(0,0,0,0.1);
                border-radius: 16px; 
            }}
            
            QLineEdit {{ 
                font-size: 11pt; 
                background: {t['input_bg']}; 
                border: 1px solid rgba(0,0,0,0.05); 
                border-radius: 8px; 
                padding: 8px 12px; 
                color: {t['text_main']}; 
            }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; }}
            
            QListWidget {{ background: transparent; border: none; outline: none; }}
            
            QPushButton {{ 
                font-size: 10pt; 
                background-color: {t['accent']}; 
                color: white; 
                border-radius: 8px; 
                padding: 6px 12px; 
                font-weight: bold; 
            }}
            QPushButton:hover {{ background-color: {t['accent']}ee; }}
            
            QPushButton#WinBtn {{ background-color: transparent; color: {t['text_main']}; border: none; font-size: 16px; }}
            QPushButton#WinBtn:hover {{ background-color: {t['btn_hover']}; border-radius: 15px; }}
            QPushButton#CloseBtn {{ background-color: transparent; color: {t['text_main']}; border: none; font-size: 18px; }}
            QPushButton#CloseBtn:hover {{ background-color: {t['close_hover']}; color: white; border-radius: 15px; }}
            
            QLabel {{ color: {t['text_main']}; }}
            QCheckBox {{ color: {t['text_done']}; }}
            
            QCalendarWidget QWidget {{ background-color: {t['cal_bg']}; color: {t['cal_text']}; }}
            QCalendarWidget QToolButton {{ color: {t['cal_text']}; background-color: transparent; border-radius: 4px; }}
            QCalendarWidget QToolButton:hover {{ background-color: {t['btn_hover']}; }}
            QCalendarWidget QSpinBox {{ color: {t['cal_text']}; background-color: transparent; }}
            QCalendarWidget QTableView {{ 
                background-color: {t['cal_bg']}; 
                gridline-color: transparent; 
                selection-background-color: transparent; 
                outline: none; 
            }}
        """
        self.setStyleSheet(style)
        self.left_container.setObjectName("LeftContainer")
        self.right_container.setObjectName("RightContainer")
        self.btn_min.setObjectName("WinBtn"); self.btn_close.setObjectName("CloseBtn")
        self.title_label.setStyleSheet(f"font-weight: bold; font-size: 16pt; color: {t['accent']}; margin-bottom: 5px;")
        self.selected_date_label.setStyleSheet(f"font-weight: bold; margin-top: 10px; color: {t['accent']}; font-size: 12pt;")
        self.sep_line.setStyleSheet(f"background-color: rgba(0,0,0,0.1); min-height: 1px; max-height: 1px;")

    def handle_smart_add(self):
        text = self.input_box.text().strip()
        if not text: return
        
        target_date = None
        time_str = ""
        priority = 0
        content = text

        # 1. 解析日期 (MMDD)
        date_match = re.search(r'^(\d{1,2})[.\s]?(\d{1,2})', content)
        if date_match:
            try:
                m, d = int(date_match.group(1)), int(date_match.group(2))
                now = datetime.now()
                y = now.year + (1 if m < now.month else 0)
                if QDate.isValid(y, m, d):
                    target_date = QDate(y, m, d)
                    content = content[date_match.span()[1]:].strip()
            except: pass

        # 2. 解析时间 (HH:mm)
        time_match = re.search(r'(\d{1,2})[:：](\d{2})', content)
        if time_match:
            time_str = f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}"
            content = content.replace(time_match.group(0), "").strip()

        # 3. 解析优先级 (!1, !2, !3)
        p_match = re.search(r'!([123])', content)
        if p_match:
            priority = int(p_match.group(1))
            content = content.replace(p_match.group(0), "").strip()

        self.add_task_data(target_date, content, time_str, priority)
        self.input_box.clear()

    def handle_right_add(self):
        text = self.right_input.text().strip()
        if not text: return
        # 右侧添加也可以支持时间解析
        time_str = ""
        time_match = re.search(r'(\d{1,2})[:：](\d{2})', text)
        if time_match:
            time_str = f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}"
            text = text.replace(time_match.group(0), "").strip()
        
        self.add_task_data(self.current_selected_date, text, time_str)
        self.right_input.clear()

    def add_task_data(self, date, text, time="", priority=0):
        key = date.toString("yyyy-MM-dd") if date else NO_DATE_KEY
        if key not in self.tasks: self.tasks[key] = []
        self.tasks[key].append({
            "text": text, 
            "done": False, 
            "time": time, 
            "priority": priority,
            "created_at": datetime.now().timestamp()
        })
        self.save_data()
        self.refresh_all_lists()
    def refresh_all_lists(self):
        dates_with_tasks = set()
        for k, v in self.tasks.items(): 
            if k != NO_DATE_KEY and any(not t['done'] for t in v): dates_with_tasks.add(k)
        self.calendar.set_markers(dates_with_tasks); self.fill_list_widget(self.left_list, filter_date=None); self.fill_list_widget(self.right_list, filter_date=self.current_selected_date)
    def fill_list_widget(self, list_widget, filter_date=None):
        list_widget.clear()
        show_done = self.show_done_cb.isChecked()
        search_query = self.search_box.text().lower()
        t_data = THEMES[self.current_theme_idx]

        def add_item(task_data, key, idx):
            if search_query and search_query not in task_data['text'].lower():
                return False
            item = QListWidgetItem()
            widget = TaskItemWidget(
                task_data, 
                t_data, 
                lambda s, k=key, i=idx: self.toggle_task(k, i, s),
                lambda checked=False, k=key, i=idx: self.delete_task(k, i),
                lambda checked=False, k=key, i=idx: self.edit_task(k, i),
                lambda: (self.save_data(), self.refresh_all_lists())
            )
            item.setSizeHint(widget.sizeHint())
            list_widget.addItem(item)
            list_widget.setItemWidget(item, widget)
            return True

        def sort_tasks(tasks):
            # 排序逻辑：未完成优先，然后按优先级降序，再按时间升序，最后按创建时间
            return sorted(tasks, key=lambda x: (
                x.get('done', False),
                -x.get('priority', 0),
                x.get('time', '99:99'),
                x.get('created_at', 0)
            ))

        if filter_date:
            key = filter_date.toString("yyyy-MM-dd")
            tasks = self.tasks.get(key, [])
            if not tasks:
                it = QListWidgetItem("✨ 无安排")
                it.setTextAlignment(Qt.AlignCenter)
                list_widget.addItem(it)
            else:
                sorted_tasks = sort_tasks(tasks)
                for i, t in enumerate(tasks): # 注意：这里索引会乱，我们需要重新设计 toggle/delete
                    # 为了简单起见，我们直接在 tasks 中找到对应的原始索引，或者重新构建 tasks
                    pass
                # 重新设计：直接遍历排序后的列表，并传递任务对象引用
                for t in sorted_tasks:
                    if not show_done and t['done']: continue
                    # 找到原始索引以支持 toggle/delete
                    orig_idx = tasks.index(t)
                    add_item(t, key, orig_idx)
            return

        # 全部待办列表
        # 1. 无日期任务
        no_date = self.tasks.get(NO_DATE_KEY, [])
        sorted_nd = sort_tasks(no_date)
        has_visible_nd = False
        for t in sorted_nd:
            if not show_done and t['done']: continue
            if search_query and search_query not in t['text'].lower(): continue
            if not has_visible_nd:
                h = QListWidgetItem()
                l = QLabel("📌 待办 (无日期)")
                l.setStyleSheet(f"color:#E6A23C;font-weight:bold;margin-top:10px; font-size: 11pt;")
                h.setSizeHint(l.sizeHint())
                list_widget.addItem(h)
                list_widget.setItemWidget(h, l)
                has_visible_nd = True
            orig_idx = no_date.index(t)
            add_item(t, NO_DATE_KEY, orig_idx)

        # 2. 有日期任务
        sorted_dates = sorted([k for k in self.tasks.keys() if k != NO_DATE_KEY])
        today_str = QDate.currentDate().toString("yyyy-MM-dd")
        for d_str in sorted_dates:
            if d_str < today_str and not show_done: continue 
            tasks = self.tasks[d_str]
            sorted_t = sort_tasks(tasks)
            
            has_visible = False
            for t in sorted_t:
                if not show_done and t['done']: continue
                if search_query and search_query not in t['text'].lower(): continue
                
                if not has_visible:
                    dob = QDate.fromString(d_str, "yyyy-MM-dd")
                    title = f"{dob.toString('M月d日 ddd')}"
                    if d_str == today_str: title += " (今天)"
                    h = QListWidgetItem()
                    l = QLabel(title)
                    l.setStyleSheet(f"color:{t_data['accent']};font-weight:bold;margin-top:10px; font-size: 11pt;")
                    h.setSizeHint(l.sizeHint())
                    list_widget.addItem(h)
                    list_widget.setItemWidget(h, l)
                    has_visible = True
                
                orig_idx = tasks.index(t)
                add_item(t, d_str, orig_idx)

    def edit_task(self, key, index):
        if key in self.tasks and index < len(self.tasks[key]):
            task = self.tasks[key][index]
            dialog = EditTaskDialog(THEMES[self.current_theme_idx], task['text'], task.get('time', ""))
            dialog.move(self.geometry().center() - dialog.rect().center())
            if dialog.exec():
                task['text'] = dialog.edit_text.text().strip()
                task['time'] = dialog.edit_time.text().strip()
                self.save_data()
                self.refresh_all_lists()

    def clear_completed_tasks(self):
        reply = QMessageBox.question(self, "确认", "确定要删除所有已完成的任务吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for key in list(self.tasks.keys()):
                self.tasks[key] = [t for t in self.tasks[key] if not t.get('done')]
                if not self.tasks[key]: del self.tasks[key]
            self.save_data()
            self.refresh_all_lists()

    def delete_task(self, key, index):
        if key in self.tasks and index < len(self.tasks[key]):
            del self.tasks[key][index]
            if not self.tasks[key]: del self.tasks[key]
            self.save_data()
            self.refresh_all_lists()

    def toggle_task(self, key, index, state):
        if key in self.tasks and index < len(self.tasks[key]):
            self.tasks[key][index]['done'] = (state == 2)
            self.save_data()
            self.refresh_all_lists()
    def on_date_selected(self, date): self.current_selected_date = date; self.selected_date_label.setText(f"📅 {date.toString('M月d日')} 的安排"); self.refresh_all_lists()
    def save_data(self):
        data = {"tasks": self.tasks, "settings": self.settings}
        try: 
            with open(self.data_file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass
    def load_data(self):
        if os.path.exists(self.data_file_path):
            try: 
                with open(self.data_file_path, 'r', encoding='utf-8') as f: 
                    data = json.load(f)
                    if "tasks" in data: self.tasks = data["tasks"]; self.settings = data.get("settings", {"close_action": "ask", "auto_start": False})
                    else: self.tasks = data; self.settings = {"close_action": "ask", "auto_start": False}
            except: self.tasks = {}; self.settings = {"close_action": "ask", "auto_start": False}
        else: self.tasks = {}; self.settings = {"close_action": "ask", "auto_start": False}
    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = QIcon()
        if os.path.exists(ICON_FILE): icon = QIcon(ICON_FILE)
        else:
            pixmap = QPixmap(64, 64); pixmap.fill(Qt.transparent); painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing); painter.setBrush(QColor("#409EFF")); painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, 64, 64, 20, 20); painter.setPen(QPen(Qt.white, 8))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "📝"); painter.end(); icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        menu = QMenu()
        menu.addAction(QAction("显示/隐藏", self, triggered=self.toggle_visibility))
        menu.addSeparator()
        menu.addAction(QAction("退出程序", self, triggered=self.quit_app))
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_click)
        self.tray_icon.show()
    def toggle_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            # 确保显示在最前
            self.showNormal()
            self.raise_()
            self.activateWindow()
            # 如果被全屏窗口遮挡，临时置顶一下再恢复（如果没开启始终置顶的话）
            if not self.settings.get("always_on_top", False):
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
                self.show()
                QTimer.singleShot(100, lambda: self.reset_flags_after_activation())

    def reset_flags_after_activation(self):
        if not self.settings.get("always_on_top", False):
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.Trigger: self.toggle_visibility()
    def quit_app(self): self.tray_icon.hide(); QApplication.quit()
    def handle_close_request(self):
        action = self.settings.get("close_action", "ask")
        if action == "ask":
            dialog = CloseOptionDialog(THEMES[self.current_theme_idx])
            dialog.move(self.geometry().center() - dialog.rect().center())
            dialog.exec()
            if dialog.result_action:
                self.perform_close_action(dialog.result_action)
                if dialog.remember: self.settings["close_action"] = dialog.result_action; self.save_data()
        else: self.perform_close_action(action)
    def perform_close_action(self, action):
        if action == "minimize": self.hide(); self.tray_icon.showMessage("桌面日程", "程序已最小化到托盘", QSystemTrayIcon.Information, 2000)
        elif action == "quit": self.quit_app()
    def toggle_right_panel(self):
        current_w = self.width()
        if self.right_container.isVisible():
            self.right_container.setVisible(False); QApplication.processEvents() 
            new_w = max(300, current_w - 280); self.resize(new_w, self.height())
        else: self.right_container.setVisible(True); self.resize(current_w + 280, self.height())
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            edge = self.check_resize_area(e.pos())
            if edge: self.resizing = True; self.resize_edge = edge; self.resize_start_pos = e.globalPosition().toPoint(); self.resize_start_geo = self.geometry()
            else: self.resizing = False; self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()
    def mouseMoveEvent(self, e):
        if not e.buttons() & Qt.LeftButton: self.update_cursor_shape(e.pos()); return
        if self.resizing:
            d = e.globalPosition().toPoint() - self.resize_start_pos; g = self.resize_start_geo; x,y,w,h = g.x(),g.y(),g.width(),g.height()
            if "top" in self.resize_edge: h = max(400, g.height() - d.y()); y = g.bottom() - h + 1
            elif "bottom" in self.resize_edge: h = max(400, g.height() + d.y())
            if "left" in self.resize_edge: w = max(300, g.width() - d.x()); x = g.right() - w + 1
            elif "right" in self.resize_edge: w = max(300, g.width() + d.x())
            self.setGeometry(x,y,w,h); e.accept(); return
        if self.drag_pos: self.move(e.globalPosition().toPoint() - self.drag_pos); e.accept()
    def mouseReleaseEvent(self, e): self.resizing = False; self.drag_pos = None; self.setCursor(Qt.ArrowCursor)
    def check_resize_area(self, p):
        w,h = self.width(), self.height(); m = 8; x,y = p.x(), p.y(); t,b = y<m, y>h-m; l,r = x<m, x>w-m
        return "top_left" if t and l else "top_right" if t and r else "bottom_left" if b and l else "bottom_right" if b and r else "top" if t else "bottom" if b else "left" if l else "right" if r else None
    def update_cursor_shape(self, p):
        e = self.check_resize_area(p); c = {"top_left": Qt.SizeFDiagCursor, "bottom_right": Qt.SizeFDiagCursor, "top_right": Qt.SizeBDiagCursor, "bottom_left": Qt.SizeBDiagCursor, "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor, "top": Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor}
        self.setCursor(c.get(e, Qt.ArrowCursor))

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    m = QSharedMemory(APP_ID)
    if not m.create(1): sys.exit(0)
    app.setQuitOnLastWindowClosed(False)
    w = DesktopWidget(); w.show(); sys.exit(app.exec())