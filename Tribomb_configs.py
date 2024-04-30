#################################
# CSC 102 Defuse the Bomb Project
# Configuration file
# Team: 
#################################

# constants
DEBUG = False        # debug mode?
RPi = True           # is this running on the RPi?
ANIMATE = True       # animate the LCD text?
SHOW_BUTTONS = False # show the Pause and Quit buttons on the main LCD GUI?
COUNTDOWN = 300      # the initial bomb countdown value (seconds)
NUM_STRIKES = 5      # the total strikes allowed before the bomb "explodes"
NUM_PHASES = 4       # the total number of initial active bomb phases

# imports
from random import randint, shuffle, choice
from string import ascii_uppercase
if (RPi):
    import board
    from adafruit_ht16k33.segments import Seg7x4
    from digitalio import DigitalInOut, Direction, Pull
    from adafruit_matrixkeypad import Matrix_Keypad

#################################
# setup the electronic components
#################################
# 7-segment display
# 4 pins: 5V(+), GND(-), SDA, SCL
#         ----------7SEG---------
if (RPi):
    i2c = board.I2C()
    component_7seg = Seg7x4(i2c)
    # set the 7-segment display brightness (0 -> dimmest; 1 -> brightest)
    component_7seg.brightness = 0.5

# keypad
# 8 pins: 10, 9, 11, 5, 6, 13, 19, NA
#         -----------KEYPAD----------
if (RPi):
    # the pins
    keypad_cols = [DigitalInOut(i) for i in (board.D10, board.D9, board.D11)]
    keypad_rows = [DigitalInOut(i) for i in (board.D5, board.D6, board.D13, board.D19)]
    # the keys
    keypad_keys = ((1, 2, 3), (4, 5, 6), (7, 8, 9), ("*", 0, "#"))

    component_keypad = Matrix_Keypad(keypad_rows, keypad_cols, keypad_keys)

# jumper wires
# 10 pins: 14, 15, 18, 23, 24, 3V3, 3V3, 3V3, 3V3, 3V3
#          -------JUMP1------  ---------JUMP2---------
# the jumper wire pins
if (RPi):
    # the pins
    component_wires = [DigitalInOut(i) for i in (board.D14, board.D15, board.D18, board.D23, board.D24)]
    for pin in component_wires:
        # pins are input and pulled down
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

# pushbutton
# 6 pins: 4, 17, 27, 22, 3V3, 3V3
#         -BUT1- -BUT2-  --BUT3--
if (RPi):
    # the state pin (state pin is input and pulled down)
    component_button_state = DigitalInOut(board.D4)
    component_button_state.direction = Direction.INPUT
    component_button_state.pull = Pull.DOWN
    # the RGB pins
    component_button_RGB = [DigitalInOut(i) for i in (board.D17, board.D27, board.D22)]
    for pin in component_button_RGB:
        # RGB pins are output
        pin.direction = Direction.OUTPUT
        pin.value = True

# toggle switches
# 3x3 pins: 12, 16, 20, 21, 3V3, 3V3, 3V3, 3V3, GND, GND, GND, GND
#           -TOG1-  -TOG2-  --TOG3--  --TOG4--  --TOG5--  --TOG6--
if (RPi):
    # the pins
    component_toggles = [DigitalInOut(i) for i in (board.D12, board.D16, board.D20, board.D21)]
    for pin in component_toggles:
        # pins are input and pulled down
        pin.direction = Direction.INPUT
        pin.pull = Pull.DOWN

###########
# functions
###########
# generates the bomb's serial number
#  it should be made up of alphaneumeric characters, and include at least 3 digits and 3 letters
#  the sum of the digits should be in the range 1..15 to set the toggles target
#  the first three letters should be distinct and in the range 0..4 such that A=0, B=1, etc, to match the jumper wires
#  the last letter should be outside of the range
def genSerial():
    # set the digits (used in the toggle switches phase)
    serial_digits = []
    toggle_value = randint(1, 15)
    # the sum of the digits is the toggle value
    while (len(serial_digits) < 3 or toggle_value - sum(serial_digits) > 0):
        d = randint(0, min(9, toggle_value - sum(serial_digits)))
        serial_digits.append(d)

    # set the letters (used in the jumper wires phase)
    jumper_indexes = [ 0 ] * 5
    while (sum(jumper_indexes) < 3):
        jumper_indexes[randint(0, len(jumper_indexes) - 1)] = 1
    jumper_value = int("".join([ str(n) for n in jumper_indexes ]), 2)
    # the letters indicate which jumper wires must be "cut"
    jumper_letters = [ chr(i + 65) for i, n in enumerate(jumper_indexes) if n == 1 ]

    # form the serial number
    serial = [ str(d) for d in serial_digits ] + jumper_letters
    # and shuffle it
    shuffle(serial)
    # finally, add a final letter (F..Z)
    serial += [ choice([ chr(n) for n in range(70, 91) ]) ]
    # and make the serial number a string
    serial = "".join(serial)

    return serial, toggle_value, jumper_value

# generates the keypad combination from a keyword and rotation key
def genKeypadCombination():
    # encrypts a keyword using a rotation cipher
    def encrypt(keyword, rot):
        cipher = ""

        # encrypt each letter of the keyword using rot
        for c in keyword:
            cipher += chr((ord(c) - 65 + rot) % 26 + 65)

        return cipher

    # returns the keypad digits that correspond to the passphrase
    def digits(passphrase):
        combination = ""
        keys = [ None, None, "ABC", "DEF", "GHI", "JKL", "MNO", "PRS", "TUV", "WXY" ]

        # process each character of the keyword
        for c in passphrase:
            for i, k in enumerate(keys):
                if (k and c in k):
                    # map each character to its digit equivalent
                    combination += str(i)

        return combination

    # the list of keywords and matching passphrases
    keywords = { "BANDIT": "RIVER",\
                 "BUCKLE": "FADED",\
                 "CANOPY": "FOXES",\
                 "DEBATE": "THROW",\
                 "FIERCE": "TRICK",\
                 "GIFTED": "CYCLE",\
                 "IMPACT": "STOLE",\
                 "LONELY": "TOADY",\
                 "MIGHTY": "ALOOF",\
                 "NATURE": "CARVE",\
                 "REBORN": "CLIMB",\
                 "RECALL": "FEIGN",\
                 "SYSTEM": "LEAVE",\
                 "TAKING": "SPINY",\
                 "WIDELY": "BOUND",\
                 "ZAGGED": "YACHT" }
    # the rotation cipher key
    rot = randint(1, 25)

    # pick a keyword and matching passphrase
    keyword, passphrase = choice(list(keywords.items()))
    # encrypt the passphrase and get its combination
    cipher_keyword = encrypt(keyword, rot)
    combination = digits(passphrase)

    return keyword, cipher_keyword, rot, combination, passphrase

###############################
# generate the bomb's specifics
###############################
# generate the bomb's serial number (which also gets us the toggle and jumper target values)
#  serial: the bomb's serial number
#  toggles_target: the toggles phase defuse value
#  wires_target: the wires phase defuse value
serial, toggles_target, wires_target = genSerial()

# generate the combination for the keypad phase
#  keyword: the plaintext keyword for the lookup table
#  cipher_keyword: the encrypted keyword for the lookup table
#  rot: the key to decrypt the keyword
#  keypad_target: the keypad phase defuse value (combination)
#  passphrase: the target plaintext passphrase
keyword, cipher_keyword, rot, keypad_target, passphrase = genKeypadCombination()

# generate the color of the pushbutton (which determines how to defuse the phase)
button_color = choice(["R", "G", "B"])
# appropriately set the target (R is None)
button_target = None
# G is the first numeric digit in the serial number
if (button_color == "G"):
    button_target = [ n for n in serial if n.isdigit() ][0]
# B is the last numeric digit in the serial number
elif (button_color == "B"):
    button_target = [ n for n in serial if n.isdigit() ][-1]

if (DEBUG):
    print(f"Serial number: {serial}")
    print(f"Toggles target: {bin(toggles_target)[2:].zfill(4)}/{toggles_target}")
    print(f"Wires target: {bin(wires_target)[2:].zfill(5)}/{wires_target}")
    print(f"Keypad target: {keypad_target}/{passphrase}/{keyword}/{cipher_keyword}(rot={rot})")
    print(f"Button target: {button_target}")

# set the bomb's LCD bootup text
boot_text = f"Booting...\n\x00\x00"\
            f"*Kernel v3.1.4-159 loaded.\n"\
            f"Initializing subsystems...\n\x00"\
            f"*System model: 102BOMBv4.2\n"\
            f"*Serial number: {serial}\n"\
            f"Encrypting keypad...\n\x00"\
            f"*Keyword: {cipher_keyword}; key: {rot}\n"\
            f"*{' '.join(ascii_uppercase)}\n"\
            f"*{' '.join([str(n % 10) for n in range(26)])}\n"\
            f"Rendering phases...\x00"
