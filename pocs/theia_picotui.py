from picotui.screen import Screen
from picotui.widgets import Dialog, WAutoComplete

s = Screen()

s.init_tty()
s.cls()




w,h = s.screen_size()
d = Dialog(0,0,w,h)

d.add(1,1, WAutoComplete(10,'a',['pajo','majo']))



d.loop()
s.deinit_tty()
