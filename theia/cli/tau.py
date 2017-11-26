from picotui.screen import Screen
from picotui.widgets import Dialog, WLabel
import os

s = Screen()

try:
    s.init_tty()
    s.cls()
    s.attr_reset()

    d = Dialog(0, 0, 40, 20)

    ts = os.get_terminal_size()

    d.add(1, 2, WLabel('aaaa'))

    d.loop()
    print(d.childs)

finally:
    s.cursor(True)
    # s.deinit_tty()
