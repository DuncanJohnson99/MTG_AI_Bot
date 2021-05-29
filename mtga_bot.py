"""

Magic The Gathering Arena bot that auto-plays to brute force daily and weekly rewards for gold/XP.

MTGA must be in full screen mode, 1920 x 1080, on primary monitor, and graphics adjusted to low. MTGA client needs to
be already launched and signed into (or you can use a BAT file to launch this script and game simultaneously as a
scheduled task).

This bot will not work out of the box if you run it now. It's dependant on grayscale values at various points on
the screen. I'm not providing the values I used in the code, firstly because it's dependant on screen resolution and
untested on any machine other than my own, and second because I don't want just anybody who comes across this to be
able to take advantage and run a MTGA bot. I'm posting this primarily as a record of the code, not because I want to
distribute a bot. You will have to figure out the grayscale values in the Range class for yourself. I've left some
in for reference.

~ defaultroot - 8th Feb 2020

"""

from PIL import ImageGrab, ImageOps, Image
from numpy import *
import pyautogui
import PIL
import imagehash
import time
import win32api, win32con
from random import randrange
from datetime import datetime
import logging

# ----- SETTINGS -----
# These settings can be used to fine tune how the bot acts. It may be the case that the bot is clicking too fast or slow
# on your machine, resulting in loops being broken. Below are the settings that worked on my own machine.

ATTACK_PROBABILITY = 100            # Percentage chance that the bot will attack with all creatures

MAX_CARD_CYCLES = 2                 # Maximum number of times the bot will cycle through cards attempting to play them

SPEED_PLAY_CARD = 0.5               # Delay between attempting to play a card
SPEED_OPPONENT_TURN_CLICK = 1       # Delay between clicking Resolve button during opponents turn

CLICKS_DISABLED = False             # Mouse clicks will not register, for testing
MOUSE_MOVE_DISABLE = False          # Mouse movement will not register, for testing

LOG_LEVEL = logging.INFO


# ----- SET UP LOGGING -----

logger = logging.getLogger('mtgalog')
hdlr = logging.FileHandler('mtgalog.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(LOG_LEVEL)

# -------------------


class Cord:

    # Maintain co-ordinates of locations to mouse click

    play_button = (1662, 1009)          # The play button on the dashboard, bottom right
    click_to_continue = (250, 200)      # Clicking (almost) anywhere in the screen to advance (usually after a match)

    # Card positions to play. Remove [::2] for all positions (less likely to need a 2nd cycle, but slower)
    cards_in_hand = ((1000,1079), (890,1079), (1050,1079), (610,1079), (1160,1079), (720,1079), (1225,1079), (660,1079),
                     (1325,1079), (540,1079), (1425,1079), (490,1079), (1550,1079), (360,1079))

    undo_button = (1750, 950)           # Undo button when casting a spell
    order_blockers_done = (970, 840)    # Click done to auto-assign damage to multiple blockers
    resolve_button = (1770, 950)        # Resolve button, also No Blocks during opponent combat
    keep_draw = (1140, 870)             # Accept drawn cards at start of match
    pass_turn = (1850, 1030)            # Pass turn button (during both player's turns)
    smiley_face_continue = (960, 850)   # Skip on smiley face screen
    opponent_avatar = (955, 105)        # To select when attacking in case opponent has Planeswalker in play
    cancel_area = (1730, 1030)          # Just a blank area to click to cancel


class Zone:

    # Maintain co-ordinates of zones/boxes that will be snipped for image match

    play_button = (1620, 980, 1850, 1035)         # On opening screen at game launch [ FINISHED ]
    victory_result = (700, 490, 1200, 590)     # Match is over (win) and awaiting click
    defeat_result = (700, 490, 1200, 590)     # Match is over (loss) and awaiting click
    undo_button = (1658, 920, 1900, 975)           # Undo button, appears when not sufficient mana to cast card
    our_first_main_icon = (820, 855, 850, 900)        # Main phase icon, indicating your turn, or not first main
    our_second_main_icon = (1070, 860, 1100, 895)    # Second phase icon
    opp_first_main_icon = (840, 108, 870, 145)        # Opponent Main phase icon
    opp_second_main_icon = (1053, 112, 1077, 140)    # Opponent Second phase icon
    keep_hand_button = (1040, 845, 1225, 905)      # Confirms start of match Mulligan/Keep
    all_attack_button = (1700, 940, 1850, 960)
    no_blocks_button = (1658, 925, 1900, 975)
    order_blockers = (822, 846, 1080, 900)        # Screen when opponent double/triple blocks
    smiley_face = (1236, 426, 1240, 455)        # TODO: IMPLEMENT ONCE WE SEE SMILEY FACE


def leftClick():
    if CLICKS_DISABLED:
        pass
    else:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)


def doubleLeftClick():
    if CLICKS_DISABLED:
        pass
    else:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)


def mousePos(cord):
    if MOUSE_MOVE_DISABLE:
        pass
    else:
        win32api.SetCursorPos((cord[0], cord[1]))


def get_screen_snip(box):
    image = ImageGrab.grab(box)
    return image


def scan_screen():

    hash_play_0 = imagehash.average_hash(get_screen_snip(Zone.play_button))
    hash_play_1 = imagehash.average_hash(Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\play_button.PNG"))
    cutoff = 18
    if hash_play_0 - hash_play_1 < cutoff:
        print("On start screen with Play button")
        return "Start"

    hash_victory_0 = imagehash.average_hash(get_screen_snip(Zone.victory_result))
    hash_victory_1 = imagehash.average_hash(
        Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\victory_result.PNG"))
    cutoff = 15
    if hash_victory_0 - hash_victory_1 < cutoff:
        print("we have won the game")
        return "Match Victory"

    hash_defeat_0 = imagehash.average_hash(get_screen_snip(Zone.defeat_result))
    hash_defeat_1 = imagehash.average_hash(
        Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\defeat_result.PNG"))
    cutoff = 15
    if hash_defeat_0 - hash_defeat_1 < cutoff:
        print("we have lost the game")
        return "Match Defeat"

    hash_keep_hand_0 = imagehash.average_hash(get_screen_snip(Zone.keep_hand_button))
    hash_keep_hand_1 = imagehash.average_hash(Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\keep_hand_button.PNG"))
    cutoff = 12
    if hash_keep_hand_0 - hash_keep_hand_1 < cutoff:
        return "In Match"


def start_screen_actions():

    # Currently just click start, in future maybe cycle daily if not 750, confirm low graphics at startup

    print("Clicking Play Button")
    mousePos(Cord.play_button)
    time.sleep(0.5)
    leftClick()


def match_result_actions():

    # Just click anywhere to proceed and then click through rewards

    print("Clicking to continue")
    mousePos(Cord.click_to_continue)
    leftClick()
    time.sleep(4)
    rewards_actions()


def rewards_actions():

    # Click Start (Claim Prize)

    print("Clicking Play (Claim) Button")
    mousePos(Cord.play_button)
    leftClick()


def check_if_my_turn():
    hash_opp_main_0 = imagehash.average_hash(get_screen_snip(Zone.opp_first_main_icon))
    hash_opp_main_1 = imagehash.average_hash(
        Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\opp_first_main_icon.PNG"))
    cutoff = 2
    if hash_opp_main_0 - hash_opp_main_1 < cutoff:
        return False

    hash_opp_second_0 = imagehash.average_hash(get_screen_snip(Zone.opp_second_main_icon))
    hash_opp_second_1 = imagehash.average_hash(
        Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\opp_second_main_icon.PNG"))
    cutoff = 2
    if hash_opp_second_0 - hash_opp_second_1 < cutoff:
        return False

    hash_our_main_0 = imagehash.average_hash(get_screen_snip(Zone.our_first_main_icon))
    hash_our_main_1 = imagehash.average_hash(
        Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\our_first_main_icon.PNG"))
    cutoff = 2
    if hash_our_main_0 - hash_our_main_1 < cutoff:
        return True

    hash_our_second_0 = imagehash.average_hash(get_screen_snip(Zone.our_second_main_icon))
    hash_our_second_1 = imagehash.average_hash(
        Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\our_second_main_icon.PNG"))
    cutoff = 2
    if hash_our_second_0 - hash_our_second_1 < cutoff:
        return True


def match_actions():
    print("Starting match_actions...")

    time.sleep(1)

    mousePos(Cord.keep_draw)
    time.sleep(0.5)
    leftClick()

    while scan_screen() != ("Match Victory" or "Match Defeat" or "Start"):
        print("Beginning In-Match Loop")

        while not check_if_my_turn():
            print("Waiting for my turn...")

            mousePos(Cord.resolve_button)
            print("Pressing Resolve while waiting for my turn...")
            leftClick()
            time.sleep(SPEED_OPPONENT_TURN_CLICK)

        card_cycles = 1
        print("Card cycles is set to {}".format(card_cycles))

        while card_cycles <= MAX_CARD_CYCLES:

            print("Beginning card cycle phase...")

            for cord in Cord.cards_in_hand:

                if scan_screen() == "Match Victory" or scan_screen() == "Match Defeat" or scan_screen() == "Start":
                    break

                print("Checking for combat phase...")

                hash_attack_all_0 = imagehash.average_hash(get_screen_snip(Zone.all_attack_button))
                hash_attack_all_1 = imagehash.average_hash(
                    Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\all_attack_button.PNG"))
                cutoff = 10
                print(hash_attack_all_0 - hash_attack_all_1)
                if hash_attack_all_0 - hash_attack_all_1 < cutoff:
                    print("Confirmed combat phase")
                    time.sleep(1)

                    attack_prob = randrange(1, 101)
                    if attack_prob < ATTACK_PROBABILITY:
                        print(f"Attacking with all creatures (roll of {attack_prob}")
                        mousePos(Cord.resolve_button)
                        leftClick()
                        time.sleep(1)
                        mousePos(Cord.opponent_avatar)
                        leftClick()
                    else:
                        print("Clicking No Attack Button")
                        mousePos(Cord.no_attacks_button)
                        leftClick()

                    print("Incrementing card_cycles by 99 and breaking")
                    card_cycles += 99
                    break

                elif not check_if_my_turn():
                    print("My opponent's turn, so incrementing card_cycles by 99 and breaking")
                    card_cycles += 99
                    break

                time.sleep(SPEED_PLAY_CARD)
                mousePos(cord)
                doubleLeftClick()
                time.sleep(0.5)

                hash_undo_0 = imagehash.average_hash(get_screen_snip(Zone.undo_button))
                hash_undo_1 = imagehash.average_hash(
                    Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\undo_button.PNG"))
                cutoff = 18
                print(hash_undo_0 - hash_undo_1)
                if hash_undo_0 - hash_undo_1 < cutoff:
                    print("Detected Undo button, so pressing it...")
                    mousePos(Cord.undo_button)
                    leftClick()

            print("Gone through all cards in hand, so incrementing card_cycles by 1")
            card_cycles += 1
            print("Card cycles is now {}/{}".format(card_cycles, MAX_CARD_CYCLES))
            time.sleep(1)

        print("Should have completed all card_cycles, so now clicking resolve_button")
        mousePos(Cord.resolve_button)
        leftClick()

        hash_order_blockers_0 = imagehash.average_hash(get_screen_snip(Zone.order_blockers))
        hash_order_blockers_1 = imagehash.average_hash(
            Image.open(r"E:\Python\MTG_AI_Bot\MTGA Icon Snips\order_blockers.PNG"))
        cutoff = 18
        print(hash_order_blockers_0 - hash_order_blockers_1)
        if hash_order_blockers_0 - hash_order_blockers_1 < cutoff:
            print("Detected Block Order, clicking done...")
            mousePos(Cord.order_blockers_done)
            leftClick()

        print("Checking if the match is over...")
        if scan_screen() == "Match Victory" or scan_screen() == "Match Defeat":
            print("Match is over, going back to main loop")
            break


logger.info("*** Started the bot ***")

while True:
    screen = scan_screen()

    if screen == "Start":
        start_screen_actions()

    elif screen == "In Match":
        match_actions()
        logger.info(f"We're in a game!")

    elif screen == "Match Victory":
        logger.info("Match Victory")
        match_result_actions()

    elif screen == "Match Defeat":
        logger.info("Match Defeat")
        match_result_actions()

    time.sleep(1)



