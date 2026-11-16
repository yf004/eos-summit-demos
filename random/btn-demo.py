from machine import Pin, SPI
import time
import framebuf

W = 240
H = 240

spi = SPI(1, baudrate=40000000, polarity=0, phase=0,
          sck=Pin(9), mosi=Pin(6), miso=Pin(5))

dc = Pin(8, Pin.OUT)
cs = Pin(7, Pin.OUT, value=1)
rst = Pin(10, Pin.OUT)
button = Pin(0, Pin.IN, Pin.PULL_UP)

LONG_MS = 700
DOUBLE_MS = 350
DISPLAY_MS = 3000
DEBOUNCE_MS = 30

def cmd(c, data=None):
    cs.value(0)
    dc.value(0)
    spi.write(bytes([c]))
    if data is not None:
        dc.value(1)
        spi.write(data)
    cs.value(1)

def window(x, y, w, h):
    cmd(0x2A, bytes((x >> 8, x & 255, (x+w-1) >> 8, (x+w-1) & 255)))
    cmd(0x2B, bytes((y >> 8, y & 255, (y+h-1) >> 8, (y+h-1) & 255)))

rst.value(0)
time.sleep_ms(100)
rst.value(1)
time.sleep_ms(150)
cmd(0x01)
time.sleep_ms(150)
cmd(0x11)
time.sleep_ms(150)
cmd(0x3A, b'\x55')
cmd(0x36, b'\x00')
cmd(0x21)
cmd(0x29)

BG = 0x3187
FG = 0xFFFF
SCALE = 3

buf = bytearray(W * H * 2)
fb = framebuf.FrameBuffer(buf, W, H, framebuf.RGB565)

def show(msg):
    print(msg)
    fb.fill(BG)
    x = (W - len(msg) * 8 * SCALE) // 2
    y = (H - 8 * SCALE) // 2

    small = bytearray(len(msg) * 8)
    text_fb = framebuf.FrameBuffer(small, len(msg) * 8, 8, framebuf.MONO_HLSB)
    text_fb.text(msg, 0, 0, 1)

    for py in range(8):
        for px in range(len(msg) * 8):
            if text_fb.pixel(px, py):
                fb.fill_rect(x + px*SCALE, y + py*SCALE, SCALE, SCALE, FG)

    window(0, 0, W, H)
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)
    spi.write(buf)
    cs.value(1)

current = "hi!"
show(current)

last = button.value()
raw_last = last
changed_at = time.ticks_ms()
pressed_at = 0
released_at = 0
shown_at = time.ticks_ms()
clicks = 0
long_sent = False

while True:
    now = time.ticks_ms()
    raw = button.value()
    msg = None

    if raw != raw_last:
        changed_at = now
        raw_last = raw

    if raw != last and time.ticks_diff(now, changed_at) >= DEBOUNCE_MS:
        last = raw

        if last == 0:
            pressed_at = now
            long_sent = False
        else:
            if not long_sent:
                clicks += 1
                released_at = now
                if clicks == 2:
                    msg = "double click"
                    clicks = 0

    if last == 0 and not long_sent:
        if time.ticks_diff(now, pressed_at) >= LONG_MS:
            msg = "long press"
            long_sent = True
            clicks = 0

    if clicks == 1 and last == 1:
        if time.ticks_diff(now, released_at) >= DOUBLE_MS:
            msg = "click"
            clicks = 0

    if msg:
        current = msg
        shown_at = now
        show(msg)

    if current != "hi!" and time.ticks_diff(now, shown_at) >= DISPLAY_MS:
        current = "hi!"
        show("hi!")

    time.sleep_ms(10)


'''
                       START
                         |
                         v
                  Initialize SPI
                  Initialize screen
                         |
                         v
                    show("hi!")
                         |
                         v
               +-------------------+
               |     MAIN LOOP     |<------------------+
               +-------------------+                   |
                         |                             |
                         v                             |
                Read button.value()                    |
                         |                             |
                         v                             |
                 Debounce (30 ms)                      |
                         |                             |
                         v                             |
                Button state changed?                  |
                    /          \                       |
                  NO           YES                     |
                   |            |                      |
                   |            v                      |
                   |       Button pressed?             |
                   |         /       \                 |
                   |       YES        NO               |
                   |        |          |               |
                   |        v          v               |
                   |   Save press   Released after     |
                   |   timestamp    long press?        |
                   |        |        /       \         |
                   |        |      YES       NO        |
                   |        |       |         |        |
                   |        |       |         v        |
                   |        |       |    clicks += 1   |
                   |        |       |         |        |
                   |        |       |         v        |
                   |        |       |    clicks == 2?  |
                   |        |       |      /    \      |
                   |        |       |    YES     NO    |
                   |        |       |     |       |    |
                   |        |       |     v       |    |
                   |        |       | "double    |    |
                   |        |       |  click"    |    |
                   |        |       |     |       |    |
                   v        v       v     v       v    |
               +----------------------------------+    |
               |       CHECK LONG PRESS           |    |
               |                                  |    |
               | button held >= 700 ms            |    |
               | AND not already detected         |    |
               +----------------------------------+    |
                         |                             |
                   YES   |   NO                        |
                    |    |    |                        |
                    v    |    v                        |
               "long press" |                          |
                    |       |                          |
                    +---+---+                          |
                        |                              |
                        v                              |
               +------------------+                    |
               | CHECK SINGLE     |                    |
               | CLICK            |                    |
               |                  |                    |
               | clicks == 1      |                    |
               | button released  |                    |
               | >= 350 ms elapsed|                    |
               +------------------+                    |
                        |                              |
                   YES  |  NO                          |
                    |   |   |                          |
                    v   |   |                          |
                 "click"|   |                          |
                    |   |   |                          |
                    +---+---+                          |
                        |                              |
                        v                              |
                New message detected?                  |
                    /        \                         |
                  YES         NO                       |
                   |           |                       |
                   v           |                       |
              show(msg)        |                       |
              reset timer      |                       |
                   |           |                       |
                   +-----+-----+                       |
                         |                             |
                         v                             |
                 1.5 seconds elapsed                     |
                 since last event?                     |
                    /        \                         |
                  YES         NO                       |
                   |           |                       |
                   v           |                       |
               show("hi!")     |                       |
                   |           |                       |
                   +-----+-----+                       |
                         |                             |
                         +-----------------------------+
'''
