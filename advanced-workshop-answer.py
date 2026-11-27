from machine import Pin, SPI
import time
import math
import random
import framebuf

W, H = 240, 240
spi = SPI(1, baudrate=80000000, polarity=0, phase=0,
          sck=Pin(9), mosi=Pin(6), miso=Pin(5))
dc = Pin(8, Pin.OUT)
cs = Pin(7, Pin.OUT, value=1)
rst = Pin(10, Pin.OUT)
button = Pin(0, Pin.IN, Pin.PULL_UP)


def _command(code, data=None):
    """Low-level display command; workshop participants need not edit this."""
    cs.value(0)
    dc.value(0)
    spi.write(bytes([code]))
    if data is not None:
        dc.value(1)
        spi.write(data)
    cs.value(1)


def _window(x, y, width, height):
    """Select the rectangle of screen pixels that will be updated."""
    _command(0x2A, bytes((x >> 8, x & 255,
                           (x + width - 1) >> 8, (x + width - 1) & 255)))
    _command(0x2B, bytes((y >> 8, y & 255,
                           (y + height - 1) >> 8, (y + height - 1) & 255)))


def _send_pixels(data):
    """Write RGB565 pixel bytes to the selected display window."""
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)
    spi.write(data)
    cs.value(1)


def init_screen():
    """Reset and turn on the display. Call once before drawing."""
    rst.value(0)
    time.sleep_ms(100)
    rst.value(1)
    time.sleep_ms(150)
    _command(0x01)
    time.sleep_ms(150)
    _command(0x11)
    time.sleep_ms(150)
    _command(0x3A, b'\x55')
    _command(0x36, b'\x00')
    _command(0x21)
    _command(0x29)
    time.sleep_ms(100)


def rgb(r, g, b):
    """Convert red, green, blue (each 0–255) into a screen colour.

    Example: PINK = rgb(255, 154, 154)
    """
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def _colour_bytes(colour):
    return bytes((colour >> 8, colour & 255))


def fill_screen(colour):
    """Paint the entire 240x240 screen a single colour.

    Example: fill_screen(rgb(0, 0, 0))  # Black background
    """
    _window(0, 0, W, H)
    row = _colour_bytes(colour) * W
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)
    for _ in range(H):
        spi.write(row)
    cs.value(1)


def draw_rect(x, y, width, height, colour):
    """Draw a solid rectangle; (x, y) is its top-left corner.

    Example: draw_rect(20, 30, 50, 15, rgb(255, 0, 0))
    Parts outside the screen are clipped automatically.
    """
    x2 = min(W, x + width)
    y2 = min(H, y + height)
    x = max(0, x)
    y = max(0, y)
    if x >= x2 or y >= y2:
        return
    width, height = x2 - x, y2 - y
    _window(x, y, width, height)
    row = _colour_bytes(colour) * width
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)
    for _ in range(height):
        spi.write(row)
    cs.value(1)


def draw_pixel(x, y, colour):
    """Colour one pixel at (x, y). Useful for simple patterns."""
    draw_rect(x, y, 1, 1, colour)


def draw_text(message, x, y, colour, scale=2, background=None):
    """Draw text using the built-in 8x8 pixel font.

    scale=1 gives 8px-high letters; scale=2 gives 16px-high letters.
    background sets the colour behind the letters (defaults to BG).
    Example: draw_text('hello', 10, 200, rgb(255, 255, 255))
    """
    if background is None:
        background = BG
    width = len(message) * 8
    if width == 0:
        return
    raw = bytearray((width * 8 + 7) // 8)
    fb = framebuf.FrameBuffer(raw, width, 8, framebuf.MONO_HLSB)
    fb.fill(0)
    fb.text(message, 0, 0, 1)
    fg, bg = _colour_bytes(colour), _colour_bytes(background)
    for py in range(8):
        line = bytearray()
        for px in range(width):
            line.extend((fg if fb.pixel(px, py) else bg) * scale)
        for sy in range(scale):
            yy = y + py * scale + sy
            if 0 <= yy < H and 0 <= x and x + width * scale <= W:
                _window(x, yy, width * scale, 1)
                _send_pixels(line)


def button_pressed():
    """Return True while the GPIO0 button is held down.

    This button is active-low: the pin reads 0 when pressed.
    """
    return button.value() == 0


BG = rgb(0x34, 0x34, 0x3C)
EYE_TOP = (255, 154, 154)
EYE_BOTTOM = (255, 197, 141)
EYE_W, EYE_H = 68, 72
CORNER_RADIUS = 17
LEFT_X, RIGHT_X, EYE_Y = 47, 130, 84
MAX_X, MAX_Y = 12, 7

RX = LEFT_X - MAX_X
RY = EYE_Y - MAX_Y
RW = RIGHT_X + EYE_W + MAX_X - RX
RH = EYE_H + 2 * MAX_Y
BUFFER = bytearray(RW * RH * 2)
BG_ROW = _colour_bytes(BG) * RW

GRADIENT = []
for y in range(EYE_H):
    t = y / (EYE_H - 1)
    GRADIENT.append(_colour_bytes(rgb(
        int(EYE_TOP[0] + (EYE_BOTTOM[0] - EYE_TOP[0]) * t),
        int(EYE_TOP[1] + (EYE_BOTTOM[1] - EYE_TOP[1]) * t),
        int(EYE_TOP[2] + (EYE_BOTTOM[2] - EYE_TOP[2]) * t)
    )))


def _corner_inset(y, height):
    """How many pixels to trim from each side for rounded corners."""
    radius = min(CORNER_RADIUS, height // 2)
    if radius <= 0:
        return 0
    if y < radius:
        dy = radius - y - 1
    elif y >= height - radius:
        dy = y - (height - radius)
    else:
        return 0
    return radius - int(math.sqrt(max(0, radius * radius - dy * dy)))


def draw_eyes(x=0, y=0, openness=1.0):
    """Draw both eyes in one frame.

    x: horizontal gaze offset, from -MAX_X to +MAX_X.
    y: vertical gaze offset, from -MAX_Y to +MAX_Y.
    openness: 1.0 = open; 0.03 = almost fully closed.

    Examples:
        draw_eyes()                  # Look straight ahead
        draw_eyes(10, -5)           # Look right and up
        draw_eyes(0, 0, 0.1)        # Almost closed / blinking
    """
    x = max(-MAX_X, min(MAX_X, int(x)))
    y = max(-MAX_Y, min(MAX_Y, int(y)))
    openness = max(0.03, min(1.0, openness))
    height = max(2, int(EYE_H * openness))
    top = (EYE_H - height) // 2
    eye_y = EYE_Y + y - RY

    for row in range(RH):
        offset = row * RW * 2
        BUFFER[offset:offset + RW * 2] = BG_ROW
        local_y = row - eye_y - top
        if not 0 <= local_y < height:
            continue
        inset = _corner_inset(local_y, height)
        width = EYE_W - 2 * inset
        if width <= 0:
            continue
        gradient_y = max(0, min(EYE_H - 1, row - eye_y))
        pixels = GRADIENT[gradient_y] * width
        for eye_x in (LEFT_X, RIGHT_X):
            start = offset + (eye_x + x - RX + inset) * 2
            BUFFER[start:start + len(pixels)] = pixels

    _window(RX, RY, RW, RH)
    _send_pixels(BUFFER)


def ease(t):
    """Smooth a value from 0 to 1 for more natural animation.

    Linear movement changes at a constant speed. This easing curve
    starts slowly, speeds up in the middle, then slows down again.
    """
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


current_x = 0
current_y = 0



def look_at(x, y, steps=4, delay_ms=20):
    """Move smoothly from the current gaze to the target offset."""
    global current_x, current_y
    x = max(-MAX_X, min(MAX_X, int(x)))
    y = max(-MAX_Y, min(MAX_Y, int(y)))
    start_x, start_y = current_x, current_y
    steps = max(1, steps)

    for i in range(1, steps + 1):
        t = ease(i / steps)
        next_x = round(start_x + (x - start_x) * t)
        next_y = round(start_y + (y - start_y) * t)
        draw_eyes(next_x, next_y)
        time.sleep_ms(delay_ms)

    current_x, current_y = x, y


def blink(frames=5, delay_ms=15):
    """Close both eyes and open them again."""
    frames = max(2, frames)
    for i in range(frames):
        t = ease(i / (frames - 1))
        draw_eyes(current_x, current_y, 1.0 - 0.97 * t)
        time.sleep_ms(delay_ms)

    time.sleep_ms(30)

    for i in range(frames):
        t = ease(i / (frames - 1))
        draw_eyes(current_x, current_y, 0.03 + 0.97 * t)
        time.sleep_ms(delay_ms)


init_screen()
fill_screen(BG)
draw_eyes()

last_move = time.ticks_ms()
last_blink = time.ticks_ms()
move_delay = random.randint(2500, 5000)
blink_delay = random.randint(4000, 8000)
was_pressed = False

while True:
    now = time.ticks_ms()

    if time.ticks_diff(now, last_move) >= move_delay:
        look_at(random.randint(-MAX_X, MAX_X),
                random.randint(-MAX_Y, MAX_Y))
        last_move = time.ticks_ms()
        move_delay = random.randint(2500, 5000)

    if time.ticks_diff(now, last_blink) >= blink_delay:
        blink()
        last_blink = time.ticks_ms()
        blink_delay = random.randint(4000, 8000)

    pressed = button_pressed()
    if pressed and not was_pressed:
        blink()
    was_pressed = pressed

    time.sleep_ms(20)

