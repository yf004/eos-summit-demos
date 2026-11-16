
from machine import Pin, SPI
import time
import random
import math

W = 240
H = 240
R = 12
BG = 0x3187
BALL = 0xFFFF

GRAVITY = 0.35
BOUNCE = 0.82
FPS = 40

spi = SPI(1, baudrate=40000000, polarity=0, phase=0,
          sck=Pin(9), mosi=Pin(6), miso=Pin(5))

dc = Pin(8, Pin.OUT)
cs = Pin(7, Pin.OUT, value=1)
rst = Pin(10, Pin.OUT)
button = Pin(0, Pin.IN, Pin.PULL_UP)

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

def circle(x, y, color):
    for dy in range(-R, R + 1):
        dx = int(math.sqrt(R * R - dy * dy))
        fill(x - dx, y + dy, dx * 2 + 1, 1, color)

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

fill(0, 0, W, H, BG)

x = W // 2
y = H - R - 1
vy = 0
active = False
old_x = x
old_y = int(y)

def reset():
    global x, y, vy, active, old_x, old_y

    fill(0, 0, W, H, BG)

    x = random.randint(R + 5, W - R - 6)
    y = random.randint(R + 5, H // 2)
    vy = 0
    active = True

    old_x = x
    old_y = int(y)

    circle(old_x, old_y, BALL)
    print("Drop:", x, int(y))

reset()

last = button.value()
raw_last = last
changed_at = time.ticks_ms()

while True:
    now = time.ticks_ms()
    raw = button.value()

    if raw != raw_last:
        raw_last = raw
        changed_at = now

    if raw != last and time.ticks_diff(now, changed_at) >= 30:
        last = raw
        if last == 0:
            reset()

    if active:
        vy += GRAVITY
        y += vy

        if y >= H - R - 1:
            y = H - R - 1
            vy = -vy * BOUNCE

            if abs(vy) < 1.2:
                vy = 0
                active = False
                print("Stopped")

        ny = int(y)

        if ny != old_y:
            fill(old_x - R, old_y - R, R * 2 + 1, R * 2 + 1, BG)
            circle(x, ny, BALL)
            old_y = ny

    time.sleep_ms(1000 // FPS)

