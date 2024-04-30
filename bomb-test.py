from tkinter import *
import tkinter
from threading import Thread
from time import sleep
from random import randint
import board
from adafruit_ht16k33.segments import Seg7x4
from digitalio import DigitalInOut, Direction, Pull
from adafruit_matrixkeypad import Matrix_Keypad

# constants
# the bomb's initial countdown timer value (seconds)
COUNTDOWN = 300
# the maximum passphrase length
MAX_PASS_LEN = 11
# does the asterisk (*) clear the passphrase?
STAR_CLEARS_PASS = True

# the LCD display "GUI"
class Lcd(Frame):
    def __init__(self, window):
        super().__init__(window, bg="black")
        # make the GUI fullscreen
        window.attributes("-fullscreen", True)
        # a copy of the timer on the 7-segment display
        self._timer = None
        # the pushbutton's state
        self._button = None
        # setup the GUI
        self.setup()

    # sets up the LCD "GUI"
    def setup(self):
        # set column weights
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.pack(fill=BOTH, expand=True)
        # the timer
        self._ltimer = Label(self, bg="black", fg="white", font=("Courier New", 24), text="Time left: ")
        self._ltimer.grid(row=0, column=0, columnspan=2, sticky=W)
        # the keypad passphrase
        self._lkeypad = Label(self, bg="black", fg="white", font=("Courier New", 24), text="Combination: ")
        self._lkeypad.grid(row=1, column=0, columnspan=2, sticky=W)
        # the jumper wires status
        self._lwires = Label(self, bg="black", fg="white", font=("Courier New", 24), text="Wires: ")
        self._lwires.grid(row=2, column=0, columnspan=2, sticky=W)
        # the pushbutton status
        self._lbutton = Label(self, bg="black", fg="white", font=("Courier New", 24), text="Button: ")
        self._lbutton.grid(row=3, column=0, columnspan=2, sticky=W)
        # the toggle switches status
        self._ltoggles = Label(self, bg="black", fg="white", font=("Courier New", 24), text="Toggles: ")
        self._ltoggles.grid(row=4, column=0, columnspan=2, sticky=W)
        # the pause button (pauses the timer)
        self._lpause = tkinter.Button(self, bg="red", fg="white", font=("Courier New", 24), text="Pause", command=self.pause)
        self._lpause.grid(row=5, column=0, sticky=W, padx=25, pady=40)
        # the quit button
        self._lquit = tkinter.Button(self, bg="red", fg="white", font=("Courier New", 24), text="Quit", command=self.quit)
        self._lquit.grid(row=5, column=1, sticky=W, padx=25, pady=40)

    # binds the 7-segment display component to the GUI
    def setTimer(self, timer):
        self._timer = timer

    # binds the pushbutton component to the GUI
    def setButton(self, button):
        self._button = button

    # pauses the timer
    def pause(self):
        self._timer.pause()

    # quits the GUI, resetting some components
    def quit(self):
        # turn off the 7-segment display
        self._timer._display.blink_rate = 0
        self._timer._display.fill(0)
        # turn off the pushbutton's LED
        for pin in self._button._rgb:
            pin.value = True
        # close the GUI
        exit(0)

# template (superclass) for various bomb components/phases
class PhaseThread(Thread):
    def __init__(self, name):
        super().__init__(name=name, daemon=True)
        # initially, the phase thread isn't running
        self._running = False
        # phases can have values (e.g., a pushbutton can be True or False, a keypad passphrase can be some string, etc)
        self._value = None

    # resets the phase's value
    def reset(self):
        self._value = None

# the timer phase
class Timer(PhaseThread):
    def __init__(self, value, display, name="Timer"):
        super().__init__(name)
        self._value = value
        # the LCD display object
        self._display = display
        # initially, the timer isn't paused
        self._paused = False

    # updates the timer
    def update(self):
        self._min = f"{self._value // 60}".zfill(2)
        self._sec = f"{self._value % 60}".zfill(2)

    # runs the thread
    def run(self):
        self._running = True
        while (True):
            if (not self._paused):
                # update the timer and display its value on the 7-segment display
                self.update()
                self._display.print(str(self))
                # wait 1s and continue
                sleep(1)
                # stop if the timer has expired
                if (self._value == 0):
                    break
                # otherwise, 1s has elapsed
                self._value -= 1
            else:
                sleep(0.1)
        self._running = False

    # pauses and unpauses the timer
    def pause(self):
        self._paused = not self._paused
        # blink the 7-segment display when paused
        self._display.blink_rate = (2 if self._paused else 0)

    def __str__(self):
        return f"{self._min}:{self._sec}"

# the keypad phase
class Keypad(PhaseThread):
    def __init__(self, keypad, name="Keypad"):
        super().__init__(name)
        self._value = ""
        # the keypad pins
        self._keypad = keypad

    # runs the thread
    def run(self):
        self._running = True
        while (True):
            # process keys when keypad key(s) are pressed
            if (self._keypad.pressed_keys):
                # debounce
                while (self._keypad.pressed_keys):
                    try:
                        key = self._keypad.pressed_keys[0]
                    except:
                        key = ""
                    sleep(0.1)
                # do we have an asterisk (*) (and it resets the passphrase)?
                if (key == "*" and STAR_CLEARS_PASS):
                    self._value = ""
                # we haven't yet reached the max pass length (otherwise, we just ignore the keypress)
                elif (len(self._value) < MAX_PASS_LEN):
                    # log the key
                    self._value += str(key)
            sleep(0.1)
        self._running = False

    def __str__(self):
        return self._value

# the jumper wires phase
class Wires(PhaseThread):
    def __init__(self, pins, name="Wires"):
        super().__init__(name)
        self._value = ""
        # the jumper wire pins
        self._pins = pins

    # runs the thread
    def run(self):
        self._running = True
        while (True):
            # get the jumper wire states (0->False, 1->True)
            self._value = "".join([str(int(pin.value)) for pin in self._pins])
            sleep(0.1)
        self._running = False

    def __str__(self):
        return f"{self._value}/{int(self._value, 2)}"

# the pushbutton phase
class Button(PhaseThread):
    colors = [ "R", "G", "B" ]  # the button's possible colors

    def __init__(self, state, rgb, name="Button"):
        super().__init__(name)
        self._value = False
        # the pushbutton's state pin
        self._state = state
        # the pushbutton's LED pins
        self._rgb = rgb

    # runs the thread
    def run(self):
        self._running = True
        # initialize and index and counter to help iterate through the RGB colors
        rgb_index = 0
        rgb_counter = 0
        while (True):
            # set the LED to the current color
            self._rgb[0].value = False if Button.colors[rgb_index] == "R" else True
            self._rgb[1].value = False if Button.colors[rgb_index] == "G" else True
            self._rgb[2].value = False if Button.colors[rgb_index] == "B" else True
            # get the pushbutton's state
            self._value = self._state.value
            # increment the RGB counter
            rgb_counter += 1
            # switch to the next RGB color every 1s (10 * 0.1s = 1s)
            if (rgb_counter == 10):
                rgb_index = (rgb_index + 1) % len(Button.colors)
                rgb_counter = 0
            sleep(0.1)
        self._running = False

    def __str__(self):
        return "Pressed" if self._value else "Released"

# the toggle switches phase
class Toggles(PhaseThread):
    def __init__(self, pins, name="Toggles"):
        super().__init__(name)
        self._value = ""
        # the toggle switch pins
        self._pins = pins

    # runs the thread
    def run(self):
        self._running = True
        while (True):
            # get the toggle switch values (0->False, 1->True)
            self._value = "".join([str(int(pin.value)) for pin in self._pins])
            sleep(0.1)
        self._running = False

    def __str__(self):
        return f"{self._value}/{int(self._value, 2)}"

######
# MAIN

# configure and initialize the LCD GUI
WIDTH = 800
HEIGHT = 600
window = Tk()
gui = Lcd(window)

# configure and initialize the phases/components

# 7 segment display
# 4 pins: 5V(+), GND(-), SDA, SCL
#         ----------7SEG---------
i2c = board.I2C()
display = Seg7x4(i2c)
display.brightness = 0.5
timer = Timer(COUNTDOWN, display)
# bind the 7-segment display to the LCD GUI
gui.setTimer(timer)

# keypad
# 8 pins: 10, 9, 11, 5, 6, 13, 19, NA
#         -----------KEYPAD----------
keypad_cols = [DigitalInOut(i) for i in (board.D10, board.D9, board.D11)]
keypad_rows = [DigitalInOut(i) for i in (board.D5, board.D6, board.D13, board.D19)]
keypad_keys = ((1, 2, 3), (4, 5, 6), (7, 8, 9), ("*", 0, "#"))
matrix_keypad = Matrix_Keypad(keypad_rows, keypad_cols, keypad_keys)
keypad = Keypad(matrix_keypad)

# jumper wires
# 10 pins: 14, 15, 18, 23, 24, 3V3, 3V3, 3V3, 3V3, 3V3
#          -------JUMP1------  ---------JUMP2---------
wire_pins = [DigitalInOut(i) for i in (board.D14, board.D15, board.D18, board.D23, board.D24)]
for pin in wire_pins:
    pin.direction = Direction.INPUT
    pin.pull = Pull.DOWN
wires = Wires(wire_pins)

# pushbutton
# 6 pins: 4, 17, 27, 22, 3V3, 3V3
#         -BUT1- -BUT2-  --BUT3--
button_input = DigitalInOut(board.D4)
button_RGB = [DigitalInOut(i) for i in (board.D17, board.D27, board.D22)]
button_input.direction = Direction.INPUT
button_input.pull = Pull.DOWN
for pin in button_RGB:
    pin.direction = Direction.OUTPUT
    pin.value = True
button = Button(button_input, button_RGB)
# bind the pushbutton to the LCD GUI
gui.setButton(button)

# toggle switches
# 3x3 pins: 12, 16, 20, 21, 3V3, 3V3, 3V3, 3V3, GND, GND, GND, GND
#           -TOG1-  -TOG2-  --TOG3--  --TOG4--  --TOG5--  --TOG6--
toggle_pins = [DigitalInOut(i) for i in (board.D12, board.D16, board.D20, board.D21)]
for pin in toggle_pins:
    pin.direction = Direction.INPUT
    pin.pull = Pull.DOWN
toggles = Toggles(toggle_pins)

# start the phase threads
timer.start()
keypad.start()
wires.start()
button.start()
toggles.start()

# check the phase threads
def check():
    # check the countdown
    if (timer._running):
        # update the GUI
        gui._ltimer.config(text=f"Time left: {timer}")
    else:
        # if the countdown has expired, quit
        quit()
    # check the keypad
    if (keypad._running):
        # update the GUI
        gui._lkeypad.config(text=f"Combination: {keypad}")
    # check the wires
    if (wires._running):
        # update the GUI
        gui._lwires.config(text=f"Wires: {wires}")
    # check the button
    if (button._running):
        # update the GUI
        gui._lbutton.config(text=f"Button: {button}")
    # check the toggles
    if (toggles._running):
        # update the GUI
        gui._ltoggles.config(text=f"Toggles: {toggles}")

    # check again after 100ms
    gui.after(100, check)

# quits the bomb
def quit():
    # turn off the 7-segment display
    display.blink_rate = 0
    display.fill(0)
    # turn off the pushbutton's LED
    for pin in button._rgb:
        pin.value = True
    # destroy the GUI and exit the program
    window.destroy()
    exit(0)

# start checking the threads
check()
# display the LCD GUI
window.mainloop()

print("The bomb has been turned off.")

