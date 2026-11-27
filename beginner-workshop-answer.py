from machine import Pin, SPI
import time
import random
import framebuf

# lcd configuration
W, H = 240, 240
spi = SPI(1, baudrate=40000000, polarity=0, phase=0,
          sck=Pin(9), mosi=Pin(6), miso=Pin(5))
dc = Pin(8, Pin.OUT)
cs = Pin(7, Pin.OUT, value=1)
rst = Pin(10, Pin.OUT)
button = Pin(0, Pin.IN, Pin.PULL_UP)


# lcd communication
def cmd(command, data=None):
    cs.value(0)
    dc.value(0)
    spi.write(bytes((command,)))
    if data is not None:
        dc.value(1)
        spi.write(data)
    cs.value(1)


def window(x, y, w, h):
    cmd(0x2A, bytes((x >> 8, x & 255, (x+w-1) >> 8, (x+w-1) & 255)))
    cmd(0x2B, bytes((y >> 8, y & 255, (y+h-1) >> 8, (y+h-1) & 255)))


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def color_bytes(color):
    return bytes((color >> 8, color & 255))


# lcd initialisation
def init_display():
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
    time.sleep_ms(100)


# screen colours
BG = rgb565(52, 52, 60)
BLACK = rgb565(0, 0, 0)
WHITE = rgb565(240, 240, 240)


# screen drawing
def fill_screen(color):
    row = color_bytes(color) * W
    window(0, 0, W, H)
    cs.value(0)
    dc.value(0)
    spi.write(b'\x2C')
    dc.value(1)
    for _ in range(H):
        spi.write(row)
    cs.value(1)


# 8 ball drawing
def draw_filled_circle(cx, cy, radius, color):
    pixel = color_bytes(color)
    for y in range(max(0, cy-radius), min(H-1, cy+radius)+1):
        dy = y-cy
        dx = int((radius*radius-dy*dy)**0.5)
        x0 = max(0, cx-dx)
        x1 = min(W-1, cx+dx)
        if x1 >= x0:
            window(x0, y, x1-x0+1, 1)
            cmd(0x2C, pixel*(x1-x0+1))


def display_text(message):
    center_y = 165
    fg, bg, scale = WHITE, BLACK, 2
    # wrap long messages and centre the text on the screen
    char_w = 8*scale
    char_h = 8*scale
    max_chars = W//char_w
    words = message.split()
    lines = []
    current = ''
    for word in words:
        candidate = current + (' ' if current else '') + word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    start_y = center_y - len(lines)*char_h//2
    fg_bytes, bg_bytes = color_bytes(fg), color_bytes(bg)
    for line_num, line in enumerate(lines):
        src_width = len(line)*8
        if src_width == 0:
            continue
        glyphs = framebuf.FrameBuffer(bytearray(src_width*8//8),
                                      src_width, 8, framebuf.MONO_HLSB)
        glyphs.fill(0)
        glyphs.text(line, 0, 0, 1)
        out_width = src_width*scale
        out_height = 8*scale
        pixels = bytearray(bg_bytes*(out_width*out_height))
        for gy in range(8):
            for gx in range(src_width):
                if glyphs.pixel(gx, gy):
                    for sy in range(scale):
                        for sx in range(scale):
                            pos = ((gy*scale+sy)*out_width + gx*scale+sx)*2
                            pixels[pos] = fg_bytes[0]
                            pixels[pos+1] = fg_bytes[1]
        x = (W-out_width)//2
        y = start_y + line_num*char_h
        if 0 <= x and 0 <= y and x+out_width <= W and y+out_height <= H:
            window(x, y, out_width, out_height)
            cmd(0x2C, pixels)


def draw_8_symbol(cx, cy):
    # draw the number 8 inside the white circle
    size, scale = 24, 3
    fb = framebuf.FrameBuffer(bytearray(8), 8, 8, framebuf.MONO_HLSB)
    fb.fill(0)
    fb.text('8', 0, 0, 1)
    pixels = bytearray(color_bytes(WHITE)*(size*size))
    ink = color_bytes(BLACK)
    for y in range(8):
        for x in range(8):
            if fb.pixel(x, y):
                for dy in range(scale):
                    for dx in range(scale):
                        i = ((y*scale+dy)*size+x*scale+dx)*2
                        pixels[i] = ink[0]
                        pixels[i+1] = ink[1]
    window(cx-size//2, cy-size//2, size, size)
    cmd(0x2C, pixels)


def draw_8ball(offset_x=0, offset_y=0):
    cx = W//2 + offset_x
    cy = H//2 + offset_y
    draw_filled_circle(cx, cy, 108, BLACK)
    draw_filled_circle(cx, cy-43, 32, WHITE)
    draw_8_symbol(cx, cy-43)


def shake_8ball():
    shake_positions = [(-8, 0), (8, 2), (-10, -2), (10, 0),
                 (-6, 2), (6, -2), (0, 0)]
    for x, y in shake_positions:
        fill_screen(BG)
        draw_8ball(x, y)
        time.sleep_ms(40)
    fill_screen(BG)
    draw_8ball()


# 8 ball messages
messages = [
    'It is certain', 'It is decidedly so', 'Without a doubt',
    'Yes definitely', 'You may rely on it', 'As I see it, yes',
    'Most likely', 'Outlook good', 'Yes', 'Signs point to yes',
    'Reply hazy, try again', 'Ask again later',
    'Better not tell you now', 'Cannot predict now',
    'Concentrate and ask again', "Don't count on it",
    'My reply is no', 'My sources say no',
    'Outlook not so good', 'Very doubtful'
]


# program loop
def main():
    init_display()
    fill_screen(BG)
    draw_8ball()
    display_text('Press button')
    print('Magic 8 Ball ready!')

    last_pressed = False
    last_change = 0
    DEBOUNCE_MS = 200

    while True:
        pressed = button.value() == 0
        now = time.ticks_ms()
        if pressed and not last_pressed:
            if time.ticks_diff(now, last_change) > DEBOUNCE_MS:
                shake_8ball()
                message = random.choice(messages)
                display_text(message)
                print(message)
                last_change = time.ticks_ms()
        last_pressed = pressed
        time.sleep_ms(20)


main()
