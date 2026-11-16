
from machine import Pin, SPI
import time
import random
import math

W = 240
H = 240
R = 12
SPEED = 8
BG = 0x3187
BALL = 0xFFFF

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

def reset():
    global x, y, vx, vy, old_x, old_y
    fill(0, 0, W, H, BG)

    x = random.randint(R, W - R - 1)
    y = random.randint(R, H - R - 1)

    angle = random.random() * 2 * math.pi
    vx = math.cos(angle) * SPEED
    vy = math.sin(angle) * SPEED

    old_x = int(x)
    old_y = int(y)
    circle(old_x, old_y, BALL)
    print("Reset:", old_x, old_y)

reset()

running = True
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
            running = not running
            print("Running" if running else "Paused")

    if last == 0 and not long_sent:
        if time.ticks_diff(now, pressed_at) >= 700:
            reset()
            long_sent = True

    if running:
        x += vx
        y += vy

        if x <= R or x >= W - R - 1:
            vx = -vx
            x = max(R, min(W - R - 1, x))

        if y <= R or y >= H - R - 1:
            vy = -vy
            y = max(R, min(H - R - 1, y))

        nx = int(x)
        ny = int(y)

        if nx != old_x or ny != old_y:
            fill(old_x - R, old_y - R, R * 2 + 1, R * 2 + 1, BG)
            circle(nx, ny, BALL)
            old_x = nx
            old_y = ny

    time.sleep_ms(20)

