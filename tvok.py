#!/usr/bin/python3

# Simple IPTV player for sources in m3u files
# TVOK. Version 0.6.0 (2019.12.18). By Oleg Kochkin. License GPL.

import sys, vlc, os
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QMenu, QAction, QLabel, QSystemTrayIcon
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings, Qt, pyqtSlot, QTimer
from PyQt5.QtDBus import QDBusConnection, QDBusMessage, QDBusInterface, QDBusReply

WINDOW_DECORATION_HEIGHT_TITLE = 25
WINDOW_DECORATION_WIDTH_BORDER = 4
VOLUME_CHANGE=5

# Get folder with script
scriptDir = os.path.dirname(os.path.realpath(__file__))
# Config file init 
cfg=QSettings('tvok','tvok')
# Load playlist
pl = []

try:
	list = sys.argv[1]
except:
	try:
		list = scriptDir+os.path.sep+'tvok.m3u'
	except:
		print("Run example:\n\ttvok.py ChannelsFile.m3u")
		exit(1)

f = open(list)
line = f.readline()
while line:
	if "#EXTINF:" in line:
		ch = line.split(',')[1].strip()
		url = f.readline().strip()
		pl.append([ch,url])
	line = f.readline()
f.close()

class MainWindow(QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
	def createUI(self):
		self.home = os.getenv("HOME")
# vlc player init
		self.instance = vlc.Instance('-q')
		self.mediaplayer = self.instance.media_player_new()
		self.mediaplayer.set_xwindow(self.winId())
# Main window settings    
		self.widget = QWidget(self)
		self.setCentralWidget(self.widget)
		self.setWindowIcon(QIcon(scriptDir+os.path.sep+'logo.png'))
		self.resize(cfg.value('Width',456,type=int),cfg.value('Height',256,type=int))
		self.setGeometry(cfg.value('Left',456,type=int)+WINDOW_DECORATION_WIDTH_BORDER,
										cfg.value('Top',256,type=int)+WINDOW_DECORATION_HEIGHT_TITLE,
										cfg.value('Width',456,type=int),
										cfg.value('Height',256,type=int))
		pal = self.palette()
		pal.setColor(self.backgroundRole(), Qt.blue)
		self.setPalette(pal)
#    self.setAutoFillBackground(True)
		self.currentCursor = self.cursor()
# Save status audio mute
		self.AudioMuteOnStart = self.mediaplayer.audio_get_mute()
		self.AudioVolumeOnStart = self.mediaplayer.audio_get_volume()
		self.Volume = cfg.value('Volume',80,type=int)

# Registered DBUS service
		DBUSName = 'tv.ok'
		DBUSConn = QDBusConnection.connectToBus(QDBusConnection.SessionBus, DBUSName)
		DBUSConn.registerService(DBUSName)
		DBUSConn.registerObject("/", self, QDBusConnection.ExportAllContents)
# Timer 1 second init. Once second call function t1secEvent
		self.t1sec = QTimer(self)
		self.t1sec.timeout.connect(self.t1secEvent)
		self.t1sec.start(1000)
# Select channel saved previous run
		self.chNum = cfg.value('Channel',1,type=int)
		self.chChange()
		
		self.trayIcon = QSystemTrayIcon()
		self.trayIcon.setToolTip('TVOK Python')
		self.trayIcon.activated.connect (self.ToggleMute)
		self.swapIcon()
		
		self.selectChannel = ''
		self.tChSelect = QTimer(self)
		self.tChSelect.timeout.connect(self.tChSelectTimeout)

	@pyqtSlot(int)
	def channelNum(self,digit):
		if (digit >= 0) and (digit <= 9):
			self.selectChannel = self.selectChannel+str(digit)
			self.tChSelect.start(2000)

	@pyqtSlot()
	def tChSelectTimeout(self):
		self.tChSelect.stop()
		self.chNum = int (self.selectChannel)
		self.selectChannel = ''
		self.chChange()

	def swapIcon(self):
		picture = scriptDir+os.path.sep+'pics/din-on.png'
		if not self.mute(): picture = scriptDir+os.path.sep+'pics/din-off.png'
		self.trayIcon.setIcon (QIcon (picture))
		self.trayIcon.show()

	@pyqtSlot(result=bool)
	def mute(self): return self.mediaplayer.audio_get_mute()

	@pyqtSlot(result=int)
	def GetChannelNum(self): return self.chNum
	@pyqtSlot(result=str)
	def GetChannel(self): return pl[self.chNum-1][0]

	@pyqtSlot(result=int)
	def GetVolume(self): return self.mediaplayer.audio_get_volume()
	@pyqtSlot()
	def VolumeIncrease(self):
		self.mediaplayer.audio_set_volume(self.mediaplayer.audio_get_volume()+VOLUME_CHANGE)
		cfg.setValue('Volume',self.mediaplayer.audio_get_volume())
	@pyqtSlot()
	def VolumeDecrease(self):
		self.mediaplayer.audio_set_volume(self.mediaplayer.audio_get_volume()-VOLUME_CHANGE)
		cfg.setValue('Volume',self.mediaplayer.audio_get_volume())

# Once second
	def t1secEvent(self):
		if self.isFullScreen(): self.setCursor (Qt.BlankCursor)

	@pyqtSlot()
	def ToggleMute(self):
		self.mediaplayer.audio_set_mute(not self.mediaplayer.audio_get_mute())
		self.swapIcon()

	@pyqtSlot()
	def ChannelNext(self):
		self.chNum += 1
#		if self.chNum > len(pl): self.chNum = 0
		self.chChange()
		
	@pyqtSlot()
	def ChannelPrev(self):
		self.chNum -= 1
#		if self.chNum < 1: self.chNum = len(pl)
		self.chChange()

# On mouse wheel change    
	def wheelEvent(self,event):
		if event.angleDelta().y() > 0: self.ChannelNext()
		if event.angleDelta().y() < 0: self.ChannelPrev()

	@pyqtSlot()
	def ChannelRestart(self): self.chChange()

# Stop current channel and start chNum channel
	def chChange(self):
		self.mediaplayer.stop()
		if self.chNum > len(pl): self.chNum = 0
		if self.chNum < 1: self.chNum = len(pl)
#		if self.chNum > len(pl): self.chNum = len(pl)
		self.setWindowTitle(str(self.chNum)+'. '+pl[self.chNum-1][0])
		self.media = self.instance.media_new(pl[self.chNum-1][1])
		self.mediaplayer.set_media(self.media)
		playerError = self.mediaplayer.play()
		if playerError != 0: sys.exit()
		cfg.setValue('Channel',self.chNum)
		cfg.setValue('Volume',self.mediaplayer.audio_get_volume())

# If double click mouse - toggle full screen    
	def mouseDoubleClickEvent(self,event): self.ToggleFullScreen()

	@pyqtSlot()
	def ToggleFullScreen(self):
		if self.isFullScreen():
			self.showNormal()
			self.setCursor (self.currentCursor)
		else: 
			self.showFullScreen()
			self.setCursor (Qt.BlankCursor)

# Mouse pressed for context menu
	def contextMenuEvent(self, event):
		menu = QMenu(self)
# Fill channels
		index = 0
		for chs in pl:
			action = menu.addAction(chs[0])
			if index == self.chNum-1:
				menu.setActiveAction(action)
				print (index)
			index += 1
		
		menu.addSeparator()
		quitAction = menu.addAction(self.tr("Quit"))
		action = menu.exec_(self.mapToGlobal(event.pos()))
		if action: 
			value_index=1
			for value in pl:
				if value[0] == action.iconText():
					if self.chNum != value_index:
						self.chNum = value_index
						self.chChange()
					break
				else: value_index += 1
			if action == quitAction:
				self.close()

	def closeEvent(self, event):
		self.mediaplayer.stop()
		if not self.isFullScreen():
			cfg.setValue('Left',self.x())
			cfg.setValue('Top',self.y())
			cfg.setValue('Width',self.width())
			cfg.setValue('Height',self.height())
		cfg.setValue('Volume',self.mediaplayer.audio_get_volume())
		cfg.sync()
		self.mediaplayer.audio_set_mute(self.AudioMuteOnStart)
		self.mediaplayer.audio_set_volume(self.AudioVolumeOnStart)
		self.trayIcon.close()
		
app = QApplication(sys.argv)
tvok = MainWindow()
tvok.createUI()
tvok.show()
sys.exit(app.exec_())
