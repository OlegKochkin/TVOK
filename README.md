Simple IPTV player for sources in m3u files
TVOK. Version 0.6.0 (2019.12.18). By Oleg Kochkin. License GPL.

Worked on GNU/Linux Fedora 31.

Capabilities:

 - Written in Python
 - Play IPTV channels specified in the m3u (m3u8) file in the script folder or as a launch parameter.
 - Double-click full-screen switching.
 - Switching channels with the mouse wheel.
 - Switching channels through the context menu.
 - Tray shortcut to mute.
 - Remember the last selected channel number and window geometry in the configuration file.
 - Uses DBUS for external control, scripts or a remote control.

 All DBUS calls can be made using qdbus utility:
  "qdbus tv.ok / method parameters"

 DBUS methods:
 
 channelNum DIGIT
  DIGIT - 0...9
   Press numbers to select a channel.
   When the time after selecting the last digit exceeds 2 seconds, the TVOK switches to the selected channel.
  Example:
   qdbus tv.ok / channelNum 4
   0.5 seconds pause...
   qdbus tv.ok / channelNum 2
   2 seconds pause...
   Selected channel 42

 mute
   Return sound mute
  Example:
   qdbus tv.ok / mute

 GetChannelNum
   Return the current channel number
  Example:
   qdbus tv.ok / GetChannelNum

 GetChannel
   Return the current channel name

 GetVolume
   Returns the current volume level (not working yet)

 VolumeIncrease
   Volume up (not working yet)

 VolumeDecrease
   Volume down (not working yet)

 ToggleMute
   Toggle sound mute
   
 ChannelNext
   Select next channel
  
 ChannelPrev
   Select previous channel

 ChannelRestart
   Restart current channel

 ToggleFullScreen
   Toggle full screen
