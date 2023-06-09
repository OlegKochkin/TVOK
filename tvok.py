#!/usr/bin/python3

# Simple IPTV player for sources in m3u files
# TVOK. Version 0.6.2 (09.06.2023). By Oleg Kochkin. License GPL.

import sys, vlc, os, time, xml.etree.ElementTree as ET, datetime, textwrap
from PyQt5.QtWidgets import QApplication,QWidget,QMainWindow,QMenu,QAction,QLabel,QSystemTrayIcon,QFrame,QGridLayout,QBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings, Qt, pyqtSlot, QTimer
from PyQt5.QtDBus import QDBusConnection, QDBusMessage, QDBusInterface, QDBusReply, QDBus

WINDOW_DECORATION_HEIGHT_TITLE = 25
WINDOW_DECORATION_WIDTH_BORDER = 4
VOLUME_CHANGE=5
VOLUME_LEVEL=80

# Get folder with script
scriptDir = os.path.dirname(os.path.realpath(__file__))
# Config file init 
cfg = QSettings('tvok','tvok')
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
		tvg=''
		if ('tvg-id=' in line): tvg=line.split('tvg-id="')[1].split('"')[0]
		ch = line.split(',')[1].strip()
		url = f.readline().strip()
		pl.append([ch,url,tvg])
	line = f.readline()
f.close()

class MainWindow(QMainWindow):
	def __init__(self):
		super(MainWindow, self).__init__()
	def createUI(self):
		self.home = os.getenv("HOME")
# vlc player init
		self.instance = vlc.Instance('--ipv4-timeout=5000 --config=~/.config/tvok/vlcrc -q')
		self.mediaplayer = self.instance.media_player_new()
# Main window settings    
		self.gridLayout = QGridLayout(self)
		self.gridLayout.setObjectName("gridLayout")
		self.videoFrame = QFrame(self)
		self.videoFrame.setObjectName("videoFrame")
		self.gridLayout.addWidget(self.videoFrame, 0, 0, 1, 1)

		self.mediaplayer.set_xwindow(int(self.winId()))

		self.setWindowIcon(QIcon(scriptDir+os.path.sep+'pics'+os.path.sep+'logo.png'))
		self.resize(cfg.value('Width',456,type=int),cfg.value('Height',256,type=int))
		self.setGeometry(cfg.value(os.path.basename(list)+'/Left',456,type=int)+WINDOW_DECORATION_WIDTH_BORDER,
										cfg.value(os.path.basename(list)+'/Top',256,type=int)+WINDOW_DECORATION_HEIGHT_TITLE,
										cfg.value(os.path.basename(list)+'/Width',456,type=int),
										cfg.value(os.path.basename(list)+'/Height',256,type=int))
		pal = self.palette()
		pal.setColor(self.backgroundRole(), Qt.darkBlue)
		self.setPalette(pal)
		self.currentCursor = self.cursor()
# Save status audio mute
		self.AudioMuteOnStart = self.mediaplayer.audio_get_mute()
		self.AudioVolumeOnStart = self.mediaplayer.audio_get_volume()
		self.Volume = cfg.value('Volume',VOLUME_LEVEL,type=int)
		self.EpgInMenu = cfg.value(os.path.basename(list)+'/EpgInMenu',False,type=bool)

# Registered DBUS service
		DBUSName = 'tv.ok'
		DBUSConn = QDBusConnection.connectToBus(QDBusConnection.SessionBus, DBUSName)
		DBUSConn.registerService(DBUSName)
		DBUSConn.registerObject("/", self, QDBusConnection.ExportAllContents)
# Timer 1 second init. Once second call function t1secEvent
		self.t1sec = QTimer(self)
		self.t1sec.timeout.connect(self.t1secEvent)
		self.t1sec.start(1000)
		self.t1min = QTimer(self)
		self.t1min.timeout.connect(self.t1minEvent)
		self.t1min.start(60000)
# Select channel saved previous run
		self.chNum = cfg.value(os.path.basename(list)+"/Channel",1,type=int)
		self.chPrev = self.chNum + 1

		self.EPG = ET.parse(scriptDir+os.path.sep+'epg.xml')

		self.chChange()
		
		self.trayIcon = QSystemTrayIcon()
		self.trayIcon.setToolTip('TVOK '+os.path.basename(list))
		self.trayIcon.activated.connect (self.ToggleMute)
		self.swapIcon()
		
		self.selectChannel = ''
		self.tChSelect = QTimer(self)
		self.tChSelect.timeout.connect(self.tChSelectTimeout)
		
	def osdView(self,mess):
# Send OSD
# If DBUS daemon org.kochkin.okindd is running
		dbus_interface = QDBusInterface("org.kochkin.okindd", "/Text")
		if dbus_interface.isValid():
			dbus_interface.call('printText', 'Tvok', mess, 5000)

	@pyqtSlot(int)
	def channelNum(self,digit):
		if (digit >= 0) and (digit <= 9):
			self.selectChannel = self.selectChannel+str(digit)
			if int(self.selectChannel) > len(pl): self.selectChannel = self.selectChannel[:-1]
			if int(self.selectChannel) < 1: self.selectChannel = self.selectChannel[:-1]
			self.osdView(self.selectChannel+': '+pl[int(self.selectChannel)-1][0])
			self.tChSelect.start(2000)

	@pyqtSlot()
	def tChSelectTimeout(self):
		self.tChSelect.stop()
		self.chNum = int (self.selectChannel)
		self.selectChannel = ''
		self.chChange()

	def swapIcon(self):
		picture = scriptDir+os.path.sep+'pics'+os.path.sep+'din-on.png'
		if not self.mute(): picture = scriptDir+os.path.sep+'pics'+os.path.sep+'din-off.png'
		self.trayIcon.setIcon (QIcon (picture))
		self.trayIcon.show()

	@pyqtSlot(result=bool)
	def mute(self): return self.mediaplayer.audio_get_mute()

	@pyqtSlot(result=int)
	def GetChannelNum(self): return self.chNum

	@pyqtSlot(result=str)
	def GetChannelName(self): return pl[self.chNum-1][0]

	@pyqtSlot(int,result=str)
	def GetChannelProg(self,chNumber):
		rootEPG = self.EPG.getroot()
		ChName = pl[chNumber][0]
		import cr
		if (ChName in cr.ChReplace): ChName = cr.ChReplace[ChName]
#		print(ChName)
		Now = (datetime.datetime.now()).strftime("%Y%m%d%H%M%S")
		Title = ""
		ChId=pl[chNumber][2]
		for prog in rootEPG.findall("./programme/[@channel='"+ChId+"']"):
			Start=prog.get('start').split()[0]
			Stop=prog.get('stop').split()[0]
			if ((Start < Now) and (Stop > Now)):
				Title=prog.find('title').text.split(' [')[0]
		return Title

	@pyqtSlot(result=int)
	def GetVolume(self): return self.mediaplayer.audio_get_volume()
	@pyqtSlot()
	
	def VolumeIncrease(self):
		self.mediaplayer.audio_set_volume(self.mediaplayer.audio_get_volume()+VOLUME_CHANGE)
	@pyqtSlot()
	
	def VolumeDecrease(self):
		self.mediaplayer.audio_set_volume(self.mediaplayer.audio_get_volume()-VOLUME_CHANGE)

# Once second
	def t1secEvent(self):
		if self.isFullScreen():
			self.CursorOff()

# Once minute
	def t1minEvent(self):
		ChPr=self.GetChannelProg(self.chNum-1)
		DelimWin=". "
		DelimOsd="\n"
		if (ChPr == ""):
			DelimWin=""
			DelimOsd=""
		NewWindowTitle = str(self.chNum)+". "+pl[self.chNum-1][0]+DelimWin+ChPr
		if (NewWindowTitle != self.windowTitle()):
			print(self.windowTitle()+" -> "+NewWindowTitle)
			self.setWindowTitle(NewWindowTitle)
			self.osdView(str(self.chNum)+': '+pl[self.chNum-1][0]+DelimOsd+textwrap.fill(ChPr,40))

	@pyqtSlot()
	def ToggleMute(self):
		self.mediaplayer.audio_set_mute(not self.mediaplayer.audio_get_mute())
		self.swapIcon()

	@pyqtSlot()
	def ChannelNext(self):
		self.chNum += 1
		self.chChange()
		
	@pyqtSlot()
	def ChannelPrev(self):
		self.chNum -= 1
		self.chChange()

# On mouse wheel change    
	def wheelEvent(self,event):
		if event.angleDelta().y() > 0: self.ChannelNext()
		if event.angleDelta().y() < 0: self.ChannelPrev()

	@pyqtSlot()
	def ChannelRestart(self): self.chChange()

	@pyqtSlot(result=str)
	def getCrop(self):
		return self.mediaplayer.video_get_crop_geometry()

	@pyqtSlot(str)
	def setCrop(self,crop):
		self.mediaplayer.video_set_crop_geometry(crop)
		cfg.setValue(self.GetChannelName()+'/Crop',crop)
		cfg.sync()

	@pyqtSlot(result=str)
	def getAspect(self):
		return self.mediaplayer.video_get_aspect_ratio()

	@pyqtSlot(str)
	def setAspect(self,aspect):
		self.mediaplayer.video_set_aspect_ratio(aspect)

	@pyqtSlot()
	def chReconnect(self):
		self.chPrev = self.chNum + 1
		self.chChange()

# Stop current channel and start chNum channel
	def chChange(self):
		if self.chNum != self.chPrev:
			if self.chNum > len(pl): self.chNum = 1
			if self.chNum < 1: self.chNum = len(pl)
			ChPr=self.GetChannelProg(self.chNum-1)
			DelimWin=". "
			DelimOsd="\n"
			if (ChPr == ""):
				DelimWin=""
				DelimOsd=""
			self.setWindowTitle(str(self.chNum)+'. '+pl[self.chNum-1][0]+DelimWin+ChPr)
			self.osdView(str(self.chNum)+': '+pl[self.chNum-1][0]+DelimOsd+textwrap.fill(ChPr,40))
			self.mediaplayer.stop()

			self.media = self.instance.media_new(pl[self.chNum-1][1])
			self.mediaplayer.set_media(self.media)
			playerError = self.mediaplayer.play()
			self.setVolume = QTimer(self)
			self.setVolume.timeout.connect(self.setVolumeMax)
			self.setVolume.start()
#			print ("playerError = "+str(playerError))
			if playerError != 0: sys.exit()
			cfg.setValue('Channel',self.chNum)
			cfg.setValue(os.path.basename(list)+"/Channel",self.chNum)
			self.chPrev = self.chNum
			if self.isFullScreen():
				self.CursorOff()

	def setVolumeMax(self):
			self.mediaplayer.audio_set_volume(VOLUME_LEVEL)
			if self.mediaplayer.audio_get_volume() >= VOLUME_LEVEL: self.setVolume.stop()
	
# If double click mouse - toggle full screen    
	def mouseDoubleClickEvent(self,event): self.ToggleFullScreen()

	def CursorOff(self):
			self.setCursor(Qt.BlankCursor)
			QApplication.setOverrideCursor(Qt.BlankCursor)

	def CursorOn(self):
			self.setCursor(self.currentCursor)
			QApplication.setOverrideCursor(self.currentCursor)

	@pyqtSlot()
	def ToggleFullScreen(self):
		if self.isFullScreen():
			self.showNormal()
			self.CursorOn()
		else:
			self.showFullScreen()
			self.CursorOff()

# Mouse pressed for context menu
	def contextMenuEvent(self, event):
		menu = QMenu(self)
# Fill channels
		index = 0
		for chs in pl:
			# if self.EpgInMenu:
			# 	action = menu.addAction(chs[0]+" ["+textwrap.fill(self.GetChannelProg(index))+"]")
			# else:
			# 	action = menu.addAction(chs[0])
			action = menu.addAction(chs[0])
			if index == self.chNum-1:
				menu.setActiveAction(action)
#				print (index)
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
			cfg.setValue(os.path.basename(list)+'/Left',self.x())
			cfg.setValue(os.path.basename(list)+'/Top',self.y())
			cfg.setValue(os.path.basename(list)+'/Width',self.width())
			cfg.setValue(os.path.basename(list)+'/Height',self.height())
		cfg.sync()
		self.mediaplayer.audio_set_mute(self.AudioMuteOnStart)
		exit()
		
app = QApplication(sys.argv)
tvok = MainWindow()
tvok.createUI()
tvok.show()
sys.exit(app.exec_())
