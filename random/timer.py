
from machine import Pin, SPI
import time
import framebuf

spi = SPI(1, baudrate=40000000, polarity=0, phase=0,
          sck=Pin(9), mosi=Pin(6), miso=Pin(5))
dc = Pin(8, Pin.OUT)
cs = Pin(7, Pin.OUT, value=1)
rst = Pin(10, Pin.OUT)
button = Pin(0, Pin.IN, Pin.PULL_UP)

BG = 0x3187
FG = 0xFFFF
SCALE = 3

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

def fill(x, y, w, h, color):
    window(x, y, w, h)
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)
    row = bytes((color >> 8, color & 255)) * w
    for _ in range(h):
        spi.write(row)
    cs.value(1)

def show(msg):
    print(msg)
    fill(0, 100, 240, 40, BG)
    width = len(msg) * 8
    mono = bytearray(width)
    fb = framebuf.FrameBuffer(mono, width, 8, framebuf.MONO_HLSB)
    fb.text(msg, 0, 0, 1)

    x = (240 - width * SCALE) // 2
    y = 108
    row = bytearray(width * SCALE * 2)

    window(x, y, width * SCALE, 8 * SCALE)
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)

    for py in range(8):
        i = 0
        for px in range(width):
            color = FG if fb.pixel(px, py) else BG
            for _ in range(SCALE):
                row[i] = color >> 8
                row[i+1] = color & 255
                i += 2
        for _ in range(SCALE):
            spi.write(row)
    cs.value(1)

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

fill(0, 0, 240, 240, BG)

running = False
elapsed = 0
started_at = 0
last_display = -1

last = button.value()
raw_last = last
changed_at = time.ticks_ms()
pressed_at = 0
long_sent = False

while True:
    now = time.ticks_ms()
    raw = button.value()

    if raw != raw_last:
        raw_last = raw
        changed_at = now

    if raw != last and time.ticks_diff(now, changed_at) >= 30:
        last = raw

        if last == 0:
            pressed_at = now
            long_sent = False
        elif not long_sent:
            if running:
                elapsed += time.ticks_diff(now, started_at)
                running = False
                print("Paused")
            else:
                started_at = now
                running = True
                print("Started")

    if last == 0 and not long_sent:
        if time.ticks_diff(now, pressed_at) >= 700:
            running = False
            elapsed = 0
            long_sent = True
            print("Reset")

    total = elapsed
    if running:
        total += time.ticks_diff(now, started_at)

    tenths = total // 100

    if tenths != last_display:
        last_display = tenths
        minutes = tenths // 600
        seconds = (tenths // 10) % 60
        fraction = tenths % 10
        show("%02d:%02d.%d" % (minutes, seconds, fraction))

    time.sleep_ms(10)

