
from machine import Pin, SPI
import time
import random
import framebuf

W = 240
H = 240

spi = SPI(1, baudrate=40000000, polarity=0, phase=0,
          sck=Pin(9), mosi=Pin(6), miso=Pin(5))

dc = Pin(8, Pin.OUT)
cs = Pin(7, Pin.OUT, value=1)
rst = Pin(10, Pin.OUT)
button = Pin(0, Pin.IN, Pin.PULL_UP)

def rgb565(r, g, b):
    return ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)

BG = rgb565(52, 52, 60)
RED = rgb565(255, 154, 154)
GREEN = rgb565(160, 230, 180)
WHITE = rgb565(245, 245, 245)
DARK = rgb565(45, 55, 50)

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

def fill(color):
    row = bytes((color >> 8, color & 255)) * W
    window(0, 0, W, H)
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)
    for _ in range(H):
        spi.write(row)
    cs.value(1)

def text(msg, y, scale, fg, bg):
    width = len(msg) * 8
    mono = bytearray(width)
    fb = framebuf.FrameBuffer(mono, width, 8, framebuf.MONO_HLSB)
    fb.text(msg, 0, 0, 1)

    x = (W - width * scale) // 2
    row = bytearray(width * scale * 2)

    window(x, y, width * scale, 8 * scale)
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)

    for py in range(8):
        i = 0
        for px in range(width):
            c = fg if fb.pixel(px, py) else bg
            for _ in range(scale):
                row[i] = c >> 8
                row[i+1] = c & 255
                i += 2
        for _ in range(scale):
            spi.write(row)

    cs.value(1)

def screen(color, msg, scale=2, fg=WHITE):
    fill(color)
    text(msg, (H - 8 * scale) // 2, scale, fg, color)
    print(msg)

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

state = 0
start_at = 0
green_at = 0

screen(BG, "click to start")

last = button.value()
raw_last = last
changed_at = time.ticks_ms()

while True:
    now = time.ticks_ms()
    raw = button.value()

    if raw != raw_last:
        raw_last = raw
        changed_at = now

    if raw != last and time.ticks_diff(now, changed_at) >= 20:
        last = raw

        if last == 0:
            if state == 0 or state == 3:
                state = 1
                start_at = now
                delay = random.randint(2000, 5000)
                screen(RED, "wait...", 3, DARK)

            elif state == 1:
                state = 3
                screen(RED, "too early!", 2, DARK)

            elif state == 2:
                reaction = time.ticks_diff(now, green_at)
                state = 3
                screen(BG, str(reaction) + " ms", 3)
                print("Reaction:", reaction, "ms")

    if state == 1 and last == 1:
        if time.ticks_diff(now, start_at) >= delay:
            state = 2
            screen(GREEN, "CLICK!", 3, DARK)
            green_at = time.ticks_ms()

    time.sleep_ms(5)

