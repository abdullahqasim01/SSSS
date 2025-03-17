import sys
import os
import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QSplashScreen, QLabel, QProgressBar, QDesktopWidget, QPushButton, QStackedWidget, QWidget, QTextBrowser, QLineEdit, QFrame, QComboBox, QSlider, QGridLayout, QFileDialog, QMessageBox, QTextEdit
from PyQt5.QtCore import Qt, QTimer, QUrl, QThread, pyqtSignal
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.uic import loadUi
from PyQt5.QtGui import QPixmap, QMovie
from utils import api, image
import webbrowser
import shutil

pic_no = 1
images_all = []
images_search_number = 1

class ClickableLabel(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, image_url):
        super(ClickableLabel, self).__init__()
        self.image_url = image_url

    def mousePressEvent(self, event):
        self.clicked.emit(self.image_url)
        if self.styleSheet() == 'border: 5px solid #F45618;':
            self.setStyleSheet('border: none;')
        else:
            self.setStyleSheet('border: 5px solid #F45618;')
    
    def remove_border(self):
        self.setStyleSheet('border: none;')

class script_thread(QThread):
    finished_signal = pyqtSignal(int, str)

    def __init__(self, prompt, duration):
        super(script_thread, self).__init__()
        self.prompt = prompt
        self.duration = duration

    def run(self):
        exit_code, script = api.generate_script(self.prompt, self.duration)
        self.finished_signal.emit(exit_code, script)

    def stop(self):
        self.terminate()

class image_thread(QThread):
    finished_signal = pyqtSignal(int, list)

    def __init__(self, query, per_page, cse_id, gcs_api_key):
        super(image_thread, self).__init__()
        self.query = query
        self.page = per_page
        self.cse_id = cse_id
        self.gcs_api_key = gcs_api_key

    def run(self):
        global pic_no
        client = image.Client(self.cse_id, self.gcs_api_key)
        images = client.search(self.query, {'size': 'large', 'start': self.page})
        image_url = []
        for img in images:
            try:
                respose = requests.get(img['url'])
            except:
                continue
            if respose.status_code == 200:
                with open(f'temp/{pic_no}.jpg', 'wb') as f:
                    f.write(respose.content)
                image_url.append(f'temp/{pic_no}.jpg')
                pic_no += 1
        self.finished_signal.emit(0, image_url)

    
    def stop(self):
        self.terminate()

class audio_thread(QThread):
    finished_signal = pyqtSignal(int, str)

    def __init__(self, text, voice, speed, bg_music, bg_music_level):
        super(audio_thread, self).__init__()
        self.text = text
        self.voice = voice
        self.speed = speed
        self.bg_music = bg_music
        self.bg_music_level = bg_music_level

    def run(self):
        exit_code, audio = api.generate_audio(self.text, self.voice, self.speed, self.bg_music, self.bg_music_level)
        self.finished_signal.emit(exit_code, audio)

    def stop(self):
        self.terminate()

class video_thread(QThread):
    finished_signal = pyqtSignal(int, str)

    def __init__(self, image_files, voiceover_file, frame, font_name, font_size, color):
        super(video_thread, self).__init__()
        self.image_files = image_files
        self.voiceover_file = voiceover_file
        self.frame = frame
        self.font_name = font_name
        self.font_size = font_size
        self.color = color

    def run(self):
        exit_code, video_output = api.generate_video(self.image_files, self.voiceover_file, self.frame, self.font_name, self.font_size, self.color)
        self.finished_signal.emit(exit_code, video_output)

    def stop(self):
        self.exit()

class MySplashScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        loadUi('splash.ui', self)

        # Center the splash screen on the desktop
        self.centerOnScreen()

        # Find the progress bar element in the UI file
        self.progressBar = self.findChild(QProgressBar, 'progressBar')

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateProgressBar)
        self.timer.start(1)  # Update progress every 100 milliseconds

    def centerOnScreen(self):
        # Center the splash screen on the desktop
        desktop = QDesktopWidget().screenGeometry()
        splash_rect = self.geometry()
        self.move((desktop.width() - splash_rect.width()) // 2, (desktop.height() - splash_rect.height()) // 2)

    def updateProgressBar(self):
        # Update the progress bar value
        value = self.progressBar.value()
        if value < 100:
            value += 1
            self.progressBar.setValue(value)
        else:
            self.timer.stop()
            self.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('mian.ui', self)
        self.setWindowTitle('My Application')

        # frame connections
        self.script_output_frame = self.findChild(QFrame, 'script_output_frame')
        self.audio_output_frame = self.findChild(QFrame, 'audio_output_frame')
        self.images_output_frame = self.findChild(QFrame, 'images_output_frame')

        #line edit connections
        self.script_prompt_lineedit = self.findChild(QLineEdit, 'script_prompt_lineedit')
        self.openai_api_key_lineedit = self.findChild(QLineEdit, 'openai_api_key_lineedit')
        self.cse_id_lineedit = self.findChild(QLineEdit, 'cse_id_lineedit')
        self.subtitles_size_lineedit = self.findChild(QLineEdit, 'subtitles_size_lineedit')
        self.image_search_lineedit = self.findChild(QLineEdit, 'image_search_lineedit')
        self.gcs_api_key_lineedit = self.findChild(QLineEdit, 'gcs_api_key_lineedit')


        #widget connections
        self.home = self.findChild(QWidget, 'home')
        self.video = self.findChild(QWidget, 'video')
        self.info = self.findChild(QWidget, 'info')
        self.script = self.findChild(QWidget, 'script')
        self.audio = self.findChild(QWidget, 'audio')
        self.subtitles = self.findChild(QWidget, 'subtitles')
        self.images = self.findChild(QWidget, 'images')
        self.output = self.findChild(QWidget, 'output')
        self.settings = self.findChild(QWidget, 'settings')
        self.generating = self.findChild(QWidget, 'generating')
        self.video_2 = self.findChild(QWidget, 'video_2')

        #stacked widget connections
        self.main_stacked = self.findChild(QStackedWidget, 'main_stacked')
        self.video_stacked = self.findChild(QStackedWidget, 'video_stacked')
        self.image_output_stacked_widget = self.findChild(QStackedWidget, 'image_output_stacked_widget')

        #text browser connections
        self.script_output_textbrowser = self.findChild(QTextEdit, 'script_output_textbrowser')


        # button connections
        self.close_button = self.findChild(QPushButton, 'close_button')
        self.max_button = self.findChild(QPushButton, 'max_button')
        self.min_button = self.findChild(QPushButton, 'min_button')
        self.create_button = self.findChild(QPushButton, 'create_button')
        self.next_button = self.findChild(QPushButton, 'next_button')
        self.back_button = self.findChild(QPushButton, 'back_button')
        self.settings_button = self.findChild(QPushButton, 'settings_button')
        self.help_button = self.findChild(QPushButton, 'help_button')
        self.sidebar_settings_button = self.findChild(QPushButton, 'sidebar_settings_button')
        self.sidebar_help_button = self.findChild(QPushButton, 'sidebar_help_button')
        self.info_button = self.findChild(QPushButton, 'info_button')
        self.script_button = self.findChild(QPushButton, 'script_button')
        self.audio_button = self.findChild(QPushButton, 'audio_button')
        self.subtitles_button = self.findChild(QPushButton, 'subtitles_button')
        self.images_button = self.findChild(QPushButton, 'images_button')
        self.video_button = self.findChild(QPushButton, 'video_button')
        self.script_generate_button = self.findChild(QPushButton, 'script_generate_button')
        self.settings_cancel_button = self.findChild(QPushButton, 'settings_cancel_button')
        self.settings_ok_button = self.findChild(QPushButton, 'settings_ok_button')
        self.audio_generate_button = self.findChild(QPushButton, 'audio_generate_button')
        self.audio_play_button = self.findChild(QPushButton, 'audio_play_button')
        self.frame1x1_button = self.findChild(QPushButton, 'frame1x1_button')
        self.frame9x16_button = self.findChild(QPushButton, 'frame9x16_button')
        self.frame4x3_button = self.findChild(QPushButton, 'frame16x9_button')
        self.duration60_button = self.findChild(QPushButton, 'duration60_button')
        self.duration45_button = self.findChild(QPushButton, 'duration45_button')
        self.duration30_button = self.findChild(QPushButton, 'duration30_button')
        self.image_search_button = self.findChild(QPushButton, 'image_search_button')
        self.video_generate_button = self.findChild(QPushButton, 'video_generate_button')
        self.images_next_button = self.findChild(QPushButton, 'next_images_button')
        self.images_previous_button = self.findChild(QPushButton, 'previous_images_button')
        self.sidebar_cancel_button = self.findChild(QPushButton, 'sidebar_cancel_button')
        self.video_export_button = self.findChild(QPushButton, 'video_export_button')
        self.images_clear_button = self.findChild(QPushButton, 'images_clear_button')


        # label connections
        self.log = self.findChild(QLabel, 'log_label')
        self.audio_elapsed_label = self.findChild(QLabel, 'audio_elapsed_label')
        self.audio_total_label = self.findChild(QLabel, 'audio_total_label')
        self.image_count_label = self.findChild(QLabel, 'images_count_label')
        self.audio_speed_label = self.findChild(QLabel, 'audio_speed_label')
        self.bg_music_level_label = self.findChild(QLabel, 'bg_music_level_label')
        self.generating_label = self.findChild(QLabel, 'generating_label')

        #combo box connections
        self.audio_voice_combobox = self.findChild(QComboBox, 'audio_voice_combobox')
        self.subtitles_font_combobox = self.findChild(QComboBox, 'subtitles_font_combobox')
        self.subtitles_color_combobox = self.findChild(QComboBox, 'subtitles_color_combobox')
        self.bg_music_file_combobox = self.findChild(QComboBox, 'bg_music_combobox')

        #slider connections
        self.audio_timeline_slider = self.findChild(QSlider, 'audio_timeline_slider')
        self.audio_speed_slider = self.findChild(QSlider, 'audio_speed_slider')
        self.bg_music_level_slider = self.findChild(QSlider, 'bg_music_level_slider')

        # button functions
        self.create_button.clicked.connect(self.create_button_func)
        self.next_button.clicked.connect(self.next_button_func)
        self.back_button.clicked.connect(self.back_button_func)
        self.settings_button.clicked.connect(self.settings_button_func)
        self.sidebar_settings_button.clicked.connect(self.settings_button_func)
        self.settings_cancel_button.clicked.connect(self.settings_cancel_button_func)
        self.settings_ok_button.clicked.connect(self.settings_ok_button_func)
        self.script_generate_button.clicked.connect(self.script_generate_button_func)
        self.audio_generate_button.clicked.connect(self.audio_generate_button_func)
        self.audio_play_button.clicked.connect(self.audio_play_button_func)
        self.frame1x1_button.clicked.connect(lambda: self.frame_button_func(self.frame1x1_button))
        self.frame9x16_button.clicked.connect(lambda: self.frame_button_func(self.frame9x16_button))
        self.frame16x9_button.clicked.connect(lambda: self.frame_button_func(self.frame16x9_button))
        self.duration60_button.clicked.connect(lambda: self.duration_button_func(self.duration60_button))
        self.duration45_button.clicked.connect(lambda: self.duration_button_func(self.duration45_button))
        self.duration30_button.clicked.connect(lambda: self.duration_button_func(self.duration30_button))
        self.image_search_button.clicked.connect(self.image_search_button_func)
        self.video_generate_button.clicked.connect(self.video_generate_button_func)
        self.images_next_button.clicked.connect(self.image_search_button_func)
        self.images_previous_button.clicked.connect(self.image_back_button_func)
        self.help_button.clicked.connect(lambda: webbrowser.open("https://sites.google.com/view/ssss-help"))
        self.sidebar_help_button.clicked.connect(lambda: webbrowser.open("https://sites.google.com/view/ssss-help"))
        self.video_export_button.clicked.connect(self.video_export_button_func)
        self.sidebar_cancel_button.clicked.connect(self.sidebar_cancel_button_func)
        self.images_clear_button.clicked.connect(self.images_clear_button_func)


        # lineedit connections

        self.script_prompt_lineedit.returnPressed.connect(self.script_generate_button_func)
        self.image_search_lineedit.returnPressed.connect(self.image_search_button_func)
        

        # frame functions
        
        #slider functions
        self.audio_timeline_slider.sliderMoved[int].connect(lambda: self.player.setPosition(self.audio_timeline_slider.value()))
        self.audio_speed_slider.sliderMoved[int].connect(lambda: self.audio_speed_label.setText(str(self.audio_speed_slider.value() / 4)))
        self.audio_speed_slider.valueChanged.connect(lambda: self.audio_speed_label.setText(str(self.audio_speed_slider.value() / 4)))
        self.bg_music_level_slider.sliderMoved[int].connect(lambda: self.bg_music_level_label.setText(str(self.bg_music_level_slider.value())))
        self.bg_music_level_slider.valueChanged.connect(lambda: self.bg_music_level_label.setText(str(self.bg_music_level_slider.value())))



        # defaults
        # self.audio_speed_slider.setTickInterval()
        self.info_button.setEnabled(False)
        self.script_button.setEnabled(False)
        self.audio_button.setEnabled(False)
        self.subtitles_button.setEnabled(False)
        self.images_button.setEnabled(False)
        self.video_button.setEnabled(False)
        self.main_stacked.setCurrentWidget(self.home)
        self.log.setText('Press create to start')
        self.script_output_frame.hide()
        self.audio_output_frame.hide()
        self.images_output_frame.hide()
        self.frame_selected = None
        self.duration = None
        self.frame = None
        self.duration_selected = None
        self.script_output = None
        self.audio_output = None
        self.subtitles_size_lineedit.setText("50")
        self.image_page = 0
        self.image_max_pages = 0
        self.image_selected = []
        self.bg_music_level_slider.setValue(30)
        self.audio_speed_slider.setValue(4)
        self.bg_music_level_label.setText(str(self.bg_music_level_slider.value()))
        self.audio_speed_label.setText(str(self.audio_speed_slider.value() / 4))
        self.video_export_button.hide()


        global stopped
        stopped = False
        self.audio_played = False

        

        try:
            with open('settings.txt', 'r') as f:
                self.settings_text = f.read()
                self.openai_api_key = self.settings_text.split('\n')[0].split('=')[1]
                self.cse_id = self.settings_text.split('\n')[1].split('=')[1]
                self.gcs_api_key = self.settings_text.split('\n')[2].split('=')[1]
        except FileNotFoundError:
            pass
        api.openai_api = self.openai_api_key
        

        self.audio_voice_combobox.addItems(['Alloy', 'Echo', 'Fable', 'Onyx', 'Nova', 'Shimmer'])
        self.subtitles_font_combobox.addItems(['Arial', 'Comic Sans MS', 'Courier New', 'Georgia', 'Helvetica', 'Impact', 'Times New Roman', 'Trebuchet ms', 'Verdana'])
        self.subtitles_color_combobox.addItems(['White', 'Red', 'Green', 'Blue', 'Yellow', 'Cyan', 'Magenta', 'Gray'])

        #audio player
        self.player = QMediaPlayer()
        self.player.setVolume(100)

        #slider
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.move_slider)

        #check if temp folder exsits
        if not os.path.exists("temp"):
            os.makedirs("temp")


        

    # custom functions
    def closeEvent(self, event):
        api.process_kill = True

        event.accept()

    def images_clear_button_func(self):
        for img in images_all:
            img.remove_border()
        self.image_selected = []
        self.image_count_label.setText("0 Selected")
        

    def video_export_button_func(self):
        fileDialog = QFileDialog(self)
        fileDialog.setAcceptMode(QFileDialog.AcceptSave)
        filename, _ = fileDialog.getSaveFileName(self, "Save Video", self.script_prompt_lineedit.text(), "Video Files (*.mp4)")
        if filename:
            self.log.setText('Exporting Video')
            try:
                os.rename(self.video_output, filename)
            except FileExistsError:
                os.remove(filename)
                os.rename(self.video_output, filename)
            self.log.setText('Video Exported')
        else:
            self.log.setText('Export Cancelled')


    def duration_button_func(self, button):
        if self.duration_selected != None:
            self.duration_selected.setStyleSheet('''background-color:  #F45618''')
        self.duration = button.text()
        self.log.setText(f'Duration set to {self.duration}')
        self.duration_selected = button

        button.setStyleSheet('''background-color: #bd4314''')


    def frame_button_func(self, button):
        if self.frame_selected != None:
            self.frame_selected.setStyleSheet('''background-color:  #F45618''')
        self.frame = button.text()
        self.log.setText(f'Frame set to {self.frame}')
        self.frame_selected = button

        button.setStyleSheet('''background-color: #bd4314''')


    def sidebar_cancel_button_func(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        if self.video_stacked.currentWidget() == self.video_2:
            msg.setWindowTitle("Finish")
            msg.setText("Are you sure you want to Finish?")
            msg.setInformativeText("Be sure to generate and export the video. Your video is lost after this step.")
        else:
            msg.setWindowTitle("Cancel")
            msg.setText("Are you sure you want to cancel?")
            msg.setInformativeText("All progress will be lost")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.show()
        value = msg.exec_()
        if value == QMessageBox.Yes:
            if self.video_stacked.currentWidget() == self.audio:
                if self.player.state() == QMediaPlayer.PlayingState:
                    self.player.pause()
                    self.audio_play_button.setText('Play')
            self.main_stacked.setCurrentWidget(self.home)
        elif value == QMessageBox.No:
            pass

    def create_button_func(self):
        self.main_stacked.setCurrentWidget(self.video)
        self.video_stacked.setCurrentWidget(self.info)
        self.info_button.setStyleSheet('''background-color: #F45618''')

        #empty temp folder

        # Delete all contents of temp folder
        temp_folder = "temp/"
        for file_name in os.listdir(temp_folder):
            file_path = os.path.join(temp_folder, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        self.video_output = ""
        self.script_output_frame.hide()
        self.audio_output_frame.hide()
        self.images_output_frame.hide()
        self.frame_selected = None
        self.duration = None
        self.frame = None
        self.duration_selected = None
        self.script_output = None
        self.audio_output = None
        self.frame1x1_button.setStyleSheet('''background-color:  #F45618''')
        self.frame4x3_button.setStyleSheet('''background-color:  #F45618''')
        self.frame9x16_button.setStyleSheet('''background-color:  #F45618''')
        self.duration60_button.setStyleSheet('''background-color:  #F45618''')
        self.duration45_button.setStyleSheet('''background-color:  #F45618''')
        self.duration30_button.setStyleSheet('''background-color:  #F45618''')
        # self.info_button.setStyleSheet('''background:none;''')
        self.script_button.setStyleSheet('''background:none;''')
        self.audio_button.setStyleSheet('''background:none;''')
        self.subtitles_button.setStyleSheet('''background:none;''')
        self.images_button.setStyleSheet('''background:none;''')
        self.video_button.setStyleSheet('''background:none;''')
        self.subtitles_size_lineedit.setText("12")
        self.image_page = 0
        self.image_max_pages = 0
        self.image_selected = []
        self.bg_music_level_slider.setValue(30)
        self.audio_speed_slider.setValue(4)
        self.bg_music_level_label.setText(str(self.bg_music_level_slider.value()))
        self.audio_speed_label.setText(str(self.audio_speed_slider.value() / 4))
        self.video_export_button.hide()
        self.next_button.setText('Next')

    def next_button_func(self):
        if self.video_stacked.currentWidget() == self.info:
            if self.frame == None:
                self.log.setText('Please select a frame')
            elif self.duration == None:
                self.log.setText('Please select a duration')
            else:
                self.log.setText('Please Generate a script')
                self.info_button.setStyleSheet('''background-color: none''')
                self.script_button.setStyleSheet('''background-color: #F45618''')
                self.video_stacked.setCurrentWidget(self.script)

        elif self.video_stacked.currentWidget() == self.script:
            if self.script_prompt_lineedit.text() == "":
                self.log.setText('Please enter a prompt')
            elif self.script_output == None:
                self.log.setText('Please Generate a script')
            else:
                self.log.setText('Please Generate audio')
                self.script_button.setStyleSheet('''background-color: none''')
                self.audio_button.setStyleSheet('''background-color: #F45618''')
                self.video_stacked.setCurrentWidget(self.audio)

        elif self.video_stacked.currentWidget() == self.audio:
            if self.audio_output == None:
                self.log.setText('Please Generate audio')
            else:
                self.log.setText('Please Generate subtitles')
                self.audio_button.setStyleSheet('''background-color: none''')
                self.subtitles_button.setStyleSheet('''background-color: #F45618''')
                if self.player.state() == QMediaPlayer.PlayingState:
                    self.player.pause()
                    self.audio_play_button.setText('Play')
                self.video_stacked.setCurrentWidget(self.subtitles)
        elif self.video_stacked.currentWidget() == self.subtitles:
            self.subtitles_color_combobox_text = self.subtitles_color_combobox.currentText().lower()
            self.subtitles_font_combobox_text = self.subtitles_font_combobox.currentText().lower()
            self.subtitles_size_lineedit_text = self.subtitles_size_lineedit.text()
            self.log.setText('Please Generate images')
            self.subtitles_button.setStyleSheet('''background-color: none''')
            self.images_button.setStyleSheet('''background-color: #F45618''')
            self.video_stacked.setCurrentWidget(self.images)
        elif self.video_stacked.currentWidget() == self.images:
            if self.image_search_lineedit == "":
                self.log.setText('Please enter a search query')
            elif self.image_selected == []:
                self.log.setText('Please select images')
            else:
                self.log.setText('Please Generate Video')
                self.images_button.setStyleSheet('''background-color: none''')
                self.video_button.setStyleSheet('''background-color: #F45618''')
                self.next_button.setText('Finish')
                self.video_stacked.setCurrentWidget(self.video_2)
        elif self.video_stacked.currentWidget() == self.video_2:
            self.sidebar_cancel_button_func()


    def back_button_func(self):
        if self.video_stacked.currentWidget() == self.info:
            self.main_stacked.setCurrentWidget(self.home)
        elif self.video_stacked.currentWidget() == self.script:
            self.script_button.setStyleSheet('''background-color: none''')
            self.info_button.setStyleSheet('''background-color: #F45618''')
            self.video_stacked.setCurrentWidget(self.info)
        elif self.video_stacked.currentWidget() == self.audio:
            self.audio_button.setStyleSheet('''background-color: none''')
            self.script_button.setStyleSheet('''background-color: #F45618''')
            if self.player.state() == QMediaPlayer.PlayingState:
                    self.player.pause()
                    self.audio_play_button.setText('Play')
            self.video_stacked.setCurrentWidget(self.script)
        elif self.video_stacked.currentWidget() == self.subtitles:
            self.subtitles_button.setStyleSheet('''background-color: none''')
            self.audio_button.setStyleSheet('''background-color: #F45618''')
            self.video_stacked.setCurrentWidget(self.audio)
        elif self.video_stacked.currentWidget() == self.images:
            self.images_button.setStyleSheet('''background-color: none''')
            self.subtitles_button.setStyleSheet('''background-color: #F45618''')
            self.video_stacked.setCurrentWidget(self.subtitles)
        elif self.video_stacked.currentWidget() == self.video_2:
            self.video_button.setStyleSheet('''background-color: none''')
            self.images_button.setStyleSheet('''background-color: #F45618''')
            self.video_stacked.setCurrentWidget(self.images)
            self.next_button.setText('Next')

    def settings_button_func(self):
        self.before_widget = QApplication.focusWidget()
        if self.before_widget.objectName() == 'sidebar_settings_button':
            self.current_widget = self.video_stacked.currentWidget()
        if self.before_widget.objectName() == 'settings_button':
            self.current_widget = self.main_stacked.currentWidget()
        self.main_stacked.setCurrentWidget(self.settings)
        if self.video_stacked.currentWidget() == self.audio:
            if self.player.state() == QMediaPlayer.PlayingState:
                    self.player.pause()
                    self.audio_play_button.setText('Play')
        try:
            self.openai_api_key_lineedit.setText(self.openai_api_key)
            self.cse_id_lineedit.setText(self.cse_id)
            self.gcs_api_key_lineedit.setText(self.gcs_api_key)
        except AttributeError:
            pass

    def settings_cancel_button_func(self):
        if self.before_widget.objectName() == 'sidebar_settings_button':
            self.main_stacked.setCurrentWidget(self.video)
            self.video_stacked.setCurrentWidget(self.current_widget)
        if self.before_widget.objectName() == 'settings_button':
            self.main_stacked.setCurrentWidget(self.current_widget)

    def settings_ok_button_func(self):
        self.openai_api_key = self.openai_api_key_lineedit.text()
        self.cse_id = self.cse_id_lineedit.text()
        self.gcs_api_key = self.gcs_api_key_lineedit.text()

        with open('settings.txt', 'w') as f:
            f.write(f'openai_api_key={self.openai_api_key}\ncse_id={self.cse_id}\ngcs_api_key={self.gcs_api_key}')
        self.settings_cancel_button_func()

    
    def generating_frame_func(self):
        self.video_stacked.setCurrentWidget(self.generating)
        self.movie = QMovie('svgs/gene.gif')
        self.generating_label.setMovie(self.movie)
        self.movie.start()


    def script_generate_button_func(self):
        self.script_generate_button.setEnabled(False)
        prompt = self.script_prompt_lineedit.text()
        if prompt == "":
            self.log.setText('Please enter a prompt')
            self.script_generate_button.setEnabled(True)
            return
        self.log.setText('Generating Script')
        self.generating_frame_func()
        self.script_thread_r = script_thread(prompt, self.duration)
        self.script_thread_r.start()
        self.script_thread_r.finished_signal.connect(self.handle_script_generation)
        self.script_thread_r.finished_signal.connect(self.script_thread_r.quit)
        self.script_thread_r.finished_signal.connect(self.script_thread_r.wait)  
        self.script_thread_r.finished_signal.connect(self.script_thread_r.deleteLater)

        
    
    def handle_script_generation(self, exit_code, script):
        if exit_code == 0:
            self.script_output_textbrowser.setText(script)
            self.log.setText('Script Generated')
            self.script_output = script
            self.script_output_frame.show()
        else:
            self.log.setText(script)
        self.script_generate_button.setEnabled(True)
        self.video_stacked.setCurrentWidget(self.script)
        

    def audio_generate_button_func(self):
        self.generating_frame_func()
        self.audio_generate_button.setEnabled(False)
        self.log.setText('Generating Audio')
        self.audio_voice_combobox_text = self.audio_voice_combobox.currentText().lower()
        self.audio_speed_label_text = self.audio_speed_slider.value() / 4
        self.bg_music = self.bg_music_file_combobox.currentText()
        self.bg_music_level_slider_text = self.bg_music_level_slider.value() / 100
        self.player.setMedia(QMediaContent())
        self.audio_thread_r = audio_thread(self.script_output, self.audio_voice_combobox_text, self.audio_speed_label_text, self.bg_music, self.bg_music_level_slider_text)
        self.audio_thread_r.start()
        self.audio_thread_r.finished_signal.connect(self.handle_audio_generation)
        self.audio_thread_r.finished_signal.connect(self.audio_thread_r.quit)
        self.audio_thread_r.finished_signal.connect(self.audio_thread_r.wait)
        self.audio_thread_r.finished_signal.connect(self.audio_thread_r.deleteLater)

        

    def handle_audio_generation(self, exit_code, audio):
        if exit_code == 0:
            self.log.setText('Audio Generated')
            self.audio_output = audio
            self.audio_output_frame.show()
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(audio)))
            self.audio_total_label.setText(time.strftime('%M:%S', time.localtime(self.player.duration() / 1000)))
        else:
            self.log.setText(audio)
        self.audio_generate_button.setEnabled(True)
        self.video_stacked.setCurrentWidget(self.audio)
            
    

        
    def image_search_button_func(self):
        if self.image_page < self.image_max_pages:
            self.image_output_stacked_widget.setCurrentIndex(self.image_output_stacked_widget.currentIndex() + 1)
            self.image_page += 1
        else:
            self.generating_frame_func()
            self.image_max_pages += 1
            self.image_page += 1

            self.log.setText('Searching for images')
            self.image_search_button.setEnabled(False)
            image_search_lineedit_text = self.image_search_lineedit.text()
            image_search_lineedit_text = image_search_lineedit_text.replace(' ', '+')
            global images_search_number
            self.image_thread_r = image_thread(image_search_lineedit_text, images_search_number, self.cse_id, self.gcs_api_key)
            images_search_number += 10
            self.image_thread_r.start()
            self.image_thread_r.finished_signal.connect(self.handle_image_generation)
            self.image_thread_r.finished_signal.connect(self.image_thread_r.quit)
            self.image_thread_r.finished_signal.connect(self.image_thread_r.wait)
            self.image_thread_r.finished_signal.connect(self.image_thread_r.deleteLater)



    def handle_image_generation(self, exit_code, image_urls):
        global images_all
        if exit_code == 0:
            self.images_output_frame.show()
            
            row = 0
            col = 0

            index = self.image_output_stacked_widget.addWidget(QWidget())
            self.image_frame = self.image_output_stacked_widget.widget(index)
            self.image_frame.setLayout(QGridLayout())
            self.image_frame.layout().setContentsMargins(0, 0, 0, 0)
            self.image_output_stacked_widget.setCurrentIndex(index)

            image_width = 150  # The width of a single image
            max_columns = (self.image_frame.width() // image_width)   # Calculate the maximum number of columns
            
            for path in image_urls:
                images_all.append(ClickableLabel(path))
                label = images_all[-1]
                label.setScaledContents(True)
                label.setFixedSize(150, 150)
                label.setPixmap(QPixmap(path))
                label.clicked.connect(self.on_label_clicked)
                label.setAlignment(Qt.AlignCenter)

                self.image_frame.layout().addWidget(label, row, col)

                col += 1
                if col == max_columns:
                    col = 0
                    row += 1

            self.log.setText('Images Added')
        else:
            self.log.setText(image_urls)
        self.video_stacked.setCurrentWidget(self.images)
        self.image_search_button.setEnabled(True)
    
    

    def on_label_clicked(self, image_url):

        if image_url in self.image_selected:
            self.image_selected.remove(image_url)
        else:
            self.image_selected.append(image_url)
        self.image_count_label.setText(str(len(self.image_selected)) + " Selected")
    
    def image_back_button_func(self):
        if self.image_page - 1  > 0:
            self.image_output_stacked_widget.setCurrentIndex(self.image_output_stacked_widget.currentIndex() - 1)
            self.image_page -= 1

    def audio_play_button_func(self):
        if self.audio_played == False:
            self.audio_played = True
            self.play_audio()
            self.audio_play_button.setText('Pause')
        else:
            if self.player.state() == QMediaPlayer.PlayingState:
                self.player.pause()
                self.audio_play_button.setText('Play')
            else:
                self.player.play()
                self.audio_play_button.setText('Pause')
    
    def video_generate_button_func(self):
        self.generating_frame_func()
        self.video_generate_button.setEnabled(False)
        self.log.setText('Generating Video')

        font_name = self.subtitles_font_combobox.currentText().lower()
        color = self.subtitles_color_combobox.currentText().lower()
        font_size = self.subtitles_size_lineedit.text().lower()
        api.process_kill = False
        self.video_thread_r = video_thread(self.image_selected, self.audio_output, self.frame, font_name, font_size, color)
        self.video_thread_r.start()
        self.video_thread_r.finished_signal.connect(self.handle_video_generation)
        self.video_thread_r.finished_signal.connect(self.video_thread_r.quit)
        self.video_thread_r.finished_signal.connect(self.video_thread_r.wait)
        self.video_thread_r.finished_signal.connect(self.video_thread_r.deleteLater)

    def handle_video_generation(self, exit_code, video):
        self.video_generate_button.hide()
        self.video_stacked.setCurrentWidget(self.video_2)
        self.video_output = video
        self.video_generate_button.setEnabled(True)
        self.video_export_button.show()
        self.log.setText('Video Generated')

    def move_slider(self):
        if stopped:
            return
        else:
            # Update the slider
            if self.player.state() == QMediaPlayer.PlayingState:
                self.audio_timeline_slider.setMinimum(0)
                self.audio_timeline_slider.setMaximum(self.player.duration())
                slider_position = self.player.position()
                self.audio_timeline_slider.setValue(slider_position)

                current_time = time.strftime('%M:%S', time.localtime(self.player.position() / 1000))
                song_duration = time.strftime('%M:%S', time.localtime(self.player.duration() / 1000))
                self.audio_elapsed_label.setText(f"{current_time}")
                self.audio_total_label.setText(f"{song_duration}")

    def play_audio(self):
        global stopped
        stopped = False

        
        self.player.play()
        self.move_slider()
        
if __name__ == '__main__':
    app = QApplication(sys.argv)


    # Create the splash screen instance
    splash = MySplashScreen()
    splash.show()

    # Simulate some initialization or loading process
    import time
    for _ in range(20):
        time.sleep(0.1)
        app.processEvents()  # Allow the GUI to update during the sleep

    # Create the main window instance
    main_window = MainWindow()
    main_window.showMaximized()
    main_window.show()

    sys.exit(app.exec_())