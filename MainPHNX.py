import json
import re
import random
import tkinter as tk
from time import sleep
import threading
from difflib import SequenceMatcher
import os
from helpers.UtilitiesPHNX import Utility, CloseAppHandler, OpenAppHandler
from helpers.HelperPHNX import VoiceAssistantGUI, VoiceRecognition, SpeechEngine
from helpers.TimeBasedHandlePHNX import (
    TimerHandle,
    AlarmHandle,
    ReminderHandle,
    ScheduleHandle,
)
import asyncio
import websockets
import asyncio
import websockets
import json


class PhoenixAssistant:

    def __init__(
        self,
        utility,
        open_handler,
        close_handler,
        timer_handle,
        alarm_handle,
        schedule_handle,
        reminder_handle,
    ):
        self.AGREE = ["yes", "open", "yeah", "start", "launch"]
        current_dir = os.path.dirname(__file__)
        self.intents_file_path = os.path.join(current_dir, "data", "intents.json")
        self.intents = self.load_intents(self.intents_file_path)
        self.utility = utility
        self.timer_handle = timer_handle
        self.alarm_handle = alarm_handle
        self.schedule_handle = schedule_handle
        self.reminder_handle = reminder_handle
        self.tag_to_patterns = self.preprocess_patterns(self.intents)
        self.mQuery = None
        self.loop = False
        self.voice = None
        self.opn = open_handler
        self.clse = close_handler
        self.cls_print = True
        self.last_tag_response = ""

    def _calculate_similarity(self, str1, str2):
        """
        Calculate the similarity ratio between two strings.
        """
        return SequenceMatcher(None, str1, str2).ratio()

    def _execute_action(self, tag, query):
        common_tags = {
            self.utility.handle_time_based_greeting: (
                "morning",
                "afternoon",
                "evening",
            ),
            self.utility.handle_whatis_whois: ("whatis", "whois"),
            self.utility.move_direction: ("forward", "backward"),
            self.utility.perform_window_action: (
                "hide",
                "minimize",
                "maximize",
                "fullscreen",
            ),
            self.utility.sleep_phnx: ("sleepbye", "donotlisten"),
            self.hib_phnx: ("gotosleep", "hib-phnx", "shutup"),
        }
        for func, tags in common_tags.items():
            if tag in tags:
                if func == self.utility.sleep_phnx or func == self.hib_phnx:
                    func()
                elif func == self.utility.perform_window_action:
                    func(tag)
                elif func == self.utility.move_direction:
                    func(tag, query)
                elif func == self.utility.handle_whatis_whois:
                    func(query)
                else:
                    func(tag, self.tag_response)
                return
        action_map = {
            "addsong": self.utility.add_song,
            "adjustBrightness": lambda query: self.utility.adjust_brightness(query),
            "adjustVolume": lambda query: self.utility.adjust_volume(query),
            "battery": self.utility.battery_check,
            "bluetooth": self.utility.bluetooth,
            "changetab": lambda query: self.utility.change_tab(query),
            "close": lambda query, response: self.utility.close_app(query, response),
            "closeallpy": self.utility.close_all_py,
            "closebgpy": self.utility.close_bg_py,
            "closetab": self.utility.close_tab,
            "dateday": self.utility.date_day,
            "dltsong": self.utility.delete_song,
            "fullscreen": self.utility.toggle_fullscreen,
            "hide": self.utility.hide_window,
            "hotspot": self.utility.hotspot,
            "maximize": lambda x: self.utility.maximize_window(x),
            "minimize": lambda x: self.utility.minimize_window(x),
            "muteSpeaker": self.utility.mute_speaker,
            "newtab": self.utility.new_tab,
            "openelse": lambda query: self.utility.open_else(query),
            "pchibernate": self.utility.hibernatE,
            "pcrestart": self.utility.restarT,
            "pcshutdown": self.utility.shutD,
            "pcsleep": self.utility.sleeP,
            "phnxrestart": self.utility.restart_phoenix,
            "playpause": lambda query: self.utility.play_pause_action(query),
            "playsong": lambda query: self.utility.play_random_song(query),
            "weather": lambda query: self.utility.weather_check(query),
            "greet-to": lambda query: self.utility.greet_to(query),
            "press": self.utility.press_key,
            "saytime": self.utility.tim,
            "screenshot": self.utility.screenshot,
            "searchbrowser": self.utility.search_browser,
            "searchinsta": self.utility.search_instagram,
            "searchyoutube": self.utility.search_youtube,
            "reload-mainphoenix": self.utility.start_mainphoenix,
            # "select": lambda query, response: self.utility.select_action(
            #     query, response
            # ),
            "setTimer": lambda x: self.timer_handle.setTimer(x),
            "viewTimer": self.timer_handle.viewTimer,
            "setAlarm": lambda x: self.alarm_handle.setAlarm(x),
            "viewAlarm": self.alarm_handle.viewAlarm,
            "dltAlarm": self.alarm_handle.deleteAlarm,
            "setReminder": lambda x: self.reminder_handle.setReminder(x),
            "viewReminder": self.reminder_handle.viewReminders,
            "setfocus": self.utility.set_focus,
            "suggestsong": self.utility.suggest_song,
            "swtchTab": self.utility.switch_tab,
            "type": lambda query: self.utility.type_text(query),
            "unmuteSpeaker": self.utility.unmute_speaker,
            "viewsongs": self.utility.view_songs,
            "pinwind": self.utility.pin_wind,
            "flipkart": self.utility.flipkart,
            "amazon": self.utility.amazon,
            # "myntra": self.utility.myntra,
            "movewind": lambda x: self.utility.process_move_window(x),
            "switchdesk": lambda x: self.utility.switch_desk(x),
            "play-game": lambda x: self.utility.switch_desk(x),
            "knock-knock": self.utility.knock_knock,
            "focus-phnx": self.utility.focus_phnx,
        }
        if tag in action_map:
            if tag in [
                "adjustVolume",
                "adjustBrightness",
                "changetab",
                "playsong",
                "playpause",
                "type_text",
                "setTimer",
                "openelse",
                "setTimer",
                "setAlarm",
                "setReminder",
                "movewind",
                "switchdesk",
                "weather",
                "greet-to",
            ]:
                action_map[tag](query)
            elif tag in ["maximize", "minimize"]:
                action_map[tag](True)
            elif tag in ["open", "close", "select"]:
                action_map[tag](query, self.tag_response)
            elif tag in ["forward", "backward"]:
                action_map[tag](tag, query)
            else:
                action_map[tag]()

    def _getSentProbability(self, main_query, list_of_strings):
        """
        Compares a main string with a list of strings and returns the highest similarity probability.
        """
        if not main_query or not list_of_strings:
            raise ValueError("Both main_query and list_of_strings must be non-empty.")
        max_probability = 0
        for string in list_of_strings:
            probability = self._calculate_similarity(main_query, string) * 100
            max_probability = max(max_probability, probability)
        return max_probability

    def _get_best_matching_intent(self, sent):
        """
        This function compares the input sentence with predefined patterns associated with different tags
        to find the best matching intent. It calculates the overlap between words in the input sentence
        and words in the patterns, and selects the tag with the highest overlap.

        Find the best matching intent for the given sentence using the tag_to_patterns dictionary.

        Args:
            sent (str): The user input sentence.

        Returns:
            dict: A dictionary with the best matching tag and a response, or None if no match is found.
        """
        # Step 1: Check explicitly for "aboutme" and "whois"
        if any(
            keyword in sent.lower()
            for keyword in [
                "made you",
                "your creator",
                "your master",
                "your sir",
                "made by whom",
            ]
        ):
            response = self._get_response("aboutme")
            return {"tag": "aboutme", "response": response}

        elif "who is" in sent.lower():
            response = self._get_response("whois")
            return {"tag": "whois", "response": response}
        else:
            # Step 2: Probability-based matching for all other intents
            best_tag, highest_probability = max(
                (
                    (tag, self._getSentProbability(sent, patterns))
                    for tag, patterns in self.tag_to_patterns.items()
                ),
                key=lambda x: x[1],
                default=(None, 0),
            )
            # print(best_tag)
            if (
                best_tag == "openelse"
                or best_tag == "playsong"
                or best_tag == "setTimer"
                or best_tag == "setAlarm"
                or best_tag == "setReminder"
                # or best_tag == "whois"
                or best_tag == "aboutme"
                or best_tag == "phnxrestart"
                or best_tag == "searchbrowser"
                # or best_tag == "myntra"
                or best_tag == "amazon"
                or best_tag == "flipkart"
                or best_tag == "knock-knock"
                or best_tag == "greet-to"
                or highest_probability > 65
            ):
                response = self._get_response(best_tag)
                return {"tag": best_tag, "response": response}

        return None

    def _get_response(self, tag):
        for intent in self.intents:
            if intent["tag"] == tag:
                return random.choice(intent["responses"])

    def print_phoenixAll(self):
        from colorama import Fore, init, Style
        import os

        # Initialize colorama
        init(autoreset=True)

        list1 = [
            "   ___ _  _  ___  ___ _  _ _____  __ ",
            "  | _ \\ || |/ _ \\| __| \\| |_ _\\ \\/ / ",
            "  |  _/ __ | (_) | _|| .` || | >  <  ",
            "  |_| |_||_|\\___/|___|_|\\_|___/_/\\_\\ ",
            "                                      ",
        ]
        list2 = [
            "                                              ",
            "   _______ _   _  ___  _____ _   _ ___ _____  ",
            "  (   _   ) | | |/ _ \\|  ___) \\ | (   |_____) ",
            "   | | | || |_| | | | | |_  |  \\| || |  ___   ",
            "   | | | ||  _  | | | |  _) |     || | (___)  ",
            "   | | | || | | | |_| | |___| |\\  || | _____  ",
            "   |_| |_||_| |_|\\___/|_____)_| \\_(___|_____) ",
            "                                              ",
            "                                              ",
        ]

        list3 = [
            "  _____ __  __  _____  _____ __  __ __ _  _    ",
            "  ||_// ||==|| ((   )) ||==  ||\\\\|| || \\\\//    ",
            "  ||    ||  ||  \\\\_//  ||___ || \\|| || //\\\\    ",
        ]

        list4 = [
            "   ____  __  __   ___    ____ __  __ __ _   _   ",
            "   || \\\\ ||  ||  // \\\\  ||    ||\\ || || \\\\ //   ",
            "   ||_// ||==|| ((   )) ||==  ||\\\\|| ||  )X(    ",
            "   ||    ||  ||  \\\\_//  ||___ || \\|| || // \\\\   ",
            "                                                ",
        ]
        list5 = ["   +-+-+-+-+-+-+-+ ", "   |P|H|O|E|N|I|X| ", "   +-+-+-+-+-+-+-+ "]

        list6 = [
            "     _   _   _   _   _   _   _   ",
            "    / \\ / \\ / \\ / \\ / \\ / \\ / \\  ",
            "   ( P | H | O | E | N | I | X ) ",
            "    \\_/ \\_/ \\_/ \\_/ \\_/ \\_/ \\_/  ",
        ]

        list7 = [
            "   ___   _     ___   ____  _      _   _        ",
            "  | |_) | |_| / / \\ | |_  | |\\ | | | \\ \\_/     ",
            "  |_|   |_| | \\_\\_/ |_|__ |_| \\| |_| /_/ \\     ",
        ]
        list8 = [
            ".-.-. .-. .-. .---. .----..-. .-..-..-..-.    ",
            "| } }}{ {_} |/ {-. \\} |__}|  \\{ |{ |\\ {} /    ",
            "| |-' | { } }\\ '-} /} '__}| }\\  {| }/ {} \\    ",
            "`-'   `-' `-' `---' `----'`-' `-'`-'`-'`-'    ",
            "                                               ",
        ]

        list9 = ["|'|-|()[-|\\||>< "]

        list10 = [
            "  _     _  __   ___\\ /   ",
            " |_)|_|/ \\|_ |\\| |  X    ",
            " |  | |\\_/|__| |_|_/ \\   ",
        ]

        # Get terminal width
        terminal_width = os.get_terminal_size().columns
        # Print each line with a color and center it
        for line in list5:
            print(line.center(terminal_width))  # Change Fore.CYAN for different colors
        # print(" ", Fore.YELLOW + "=" * (terminal_width - 2))
        print(" ", "=" * (terminal_width - 2))
        return True

    def print_phoenix(self):
        terminal_width = os.get_terminal_size().columns
        print("   +-+-+-+-+-+-+-+ ".center(terminal_width))
        print("   |P|H|O|E|N|I|X| ".center(terminal_width))
        print("   +-+-+-+-+-+-+-+ ".center(terminal_width))
        print(" ", "=" * (terminal_width - 2))
        return True

    def check_cls_phnx(self):
        self.cls_print = False
        sleep(65)
        self.cls_print = True

    def reload_phnx(self):
        self.reload = False
        sleep(90)
        self.reload = True

    def cls_and_print_phnx(self):
        """
        Clears the terminal every 5 minutes.
        """
        os.system("cls" if os.name == "nt" else "clear")
        self.print_phoenix()
        # return True
        # if self.print_phoenix():
        #     sleep(1)
        #     return True

    def handle_command(self, sent):
        if sent:
            parts = [part.strip() for part in sent.split(" and ")]
            for part in parts:
                if part:
                    self.main(part)
        else:
            self.loop = False

    def input_chat(self):
        self.loop = False
        self.utility.get_window("MainPHNX.py")
        while True:
            sent = input("Enter command: ").lower().strip()
            if "switch to voice" in sent or "wake up" in sent or "stv" in sent:
                self.voice = True
                break
            self.mQuery = sent
            sent = self.remove_phoenix_except_folder(sent)
            print(sent)
            if sent:
                self.handle_command(sent)
            elif self.loop == True:
                self.handle_command(sent)
            elif not sent:
                self.loop = False
            else:
                self.loop = False

    def input_voice(self):
        self.loop = False
        while True:
            if self.voice == False:
                break
            sent = self.takeCommand().lower().strip()
            if "switch to chat" in sent:
                self.voice = False
                break
            if (
                "phoenix" in sent
                or "finish" in sent
                or "feelings" in sent
                or "feeling" in sent
                or "friend" in sent
                or "buddy" in sent
                or "love" in sent
                or "baby" in sent
            ) and self.loop == False:
                self.mQuery = sent
                sent = self.remove_phoenix_except_folder(sent)
                if sent:
                    self.handle_command(sent)
            elif self.loop == True:
                self.mQuery = sent
                self.handle_command(sent)
            elif not sent:
                self.loop = False
            else:
                self.loop = False

            if self.reload == True and not sent:
                print("Re-starting chat...")
                break

    def main_phnx(self):
        self.voice = True
        self.cls_and_print_phnx()
        threading.Thread(target=self.reload_phnx).start()
        while True:
            if self.reload == True:
                self.cls_and_print_phnx()
                threading.Thread(target=self.reload_phnx).start()
            if self.voice:
                self.input_voice()
            else:
                self.input_chat()

    def load_intents(self, file_path):
        with open(file_path, "r") as file:
            return json.load(file)["intents"]

    def hib_phnx(self):
        self.voice = False

    async def send_to_websocket(self, ai_response):
        """Send response to WebSocket."""
        uri = "ws://127.0.0.1:8765"
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(ai_response)
        except Exception as e:
            print(f"WebSocket error: {e}")

    def main(self, sent):
        no_response_tag = [
            "add",
            "focus-phnx",
            "greet-to",
            "pinwind",
            "weather",
            "addSchedule",
            "addsong",
            "backspace",
            "battery",
            "bckgrnd",
            "btrychk",
            "dateday",
            "deleteSchedule",
            "div",
            "dltAlarm",
            "dltReminder",
            "dltsong",
            "down",
            "doyouknowabout",
            "editReminder",
            "editSchedule",
            "enter",
            "fullscreen",
            "hide",
            "left",
            "maximize",
            "minimize",
            "modulo",
            "mul",
            "openelse",
            "playpause",
            "playsong",
            "press",
            "right",
            "saytime",
            "searchbrowser",
            "searchinsta",
            "searchyoutube",
            "select",
            "setAlarm",
            "setReminder",
            "setTimer",
            "sub",
            "suggestsong",
            "tmchk",
            "type",
            "up",
            "viewAlarm",
            "viewReminder",
            "viewSchedule",
            "viewTimer",
            "whatis",
            "whatyouknowabout",
            "whois",
            "wikiabout",
            "switchdesk",
            "open",
            "myntra",
            "amazon",
            "flipkart",
        ]

        query_main = self.remove_phoenix_except_folder(sent)
        query = self.remove_phoenix_except_folder(sent)
        keywords = ["open", "launch", "start"]
        for keyword in keywords:
            if keyword in query and "restart" not in query:
                self.opn.process_query(query, self.mQuery)
                return
        if "close" in query:
            self.clse.process_query(query, self.mQuery)
            return
        match = re.search(r"play (.+?) song", query)
        if match:
            query = re.sub(r"play .+? (song|music)", "play {this} song", query)
        matched_intent = self._get_best_matching_intent(query)
        if matched_intent:
            tag = matched_intent["tag"]
            self.tag_response = matched_intent["response"]
            if tag not in no_response_tag:
                self.speak(self.tag_response)
                # if not self.last_tag_response == self.tag_response:
                #     # # Use the existing event loop to send the WebSocket message
                #     # loop = asyncio.get_event_loop()
                #     # loop.run_until_complete(self.send_to_websocket(self.tag_response))
                #     return self.tag_response
                self.last_tag_response = self.tag_response
            self._execute_action(tag, query_main)
            self.loop = True
        else:
            self.loop = False

    def preprocess_patterns(self, intents):
        """
        Process intents JSON data to create a dictionary mapping tags to sets of unique pattern words.

        Args:
            intents (dict): A dictionary containing intents with tags and patterns.

        Returns:
            dict: A dictionary mapping tags to sets of unique words from their patterns.
        """
        tag_to_patterns = {}
        for intent in intents:
            tag_to_patterns[intent["tag"]] = intent["patterns"]
        return tag_to_patterns

    def remove_phoenix_except_folder(self, sent):
        """
        Remove 'phoenix' from the string except when it's part of folder name like 'phoenix folder'.
        """
        sent = re.sub(
            "(?<!\\w)phoenix(?! folder)(?!\\w)", "", sent, flags=re.IGNORECASE
        ).strip()
        return sent

    def speak(self, text, speed=174):
        self.utility.speak(text, speed)

    def takeCommand(self):
        return self.utility.take_command()

    def process_input(self, query):
        return self.main(query)


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    asutils = Utility(reco=recog, spk=spk)
    opn = OpenAppHandler(asutils)
    clse = CloseAppHandler(asutils)
    timer_handle = TimerHandle(asutils)
    alarm_handle = AlarmHandle(asutils)
    reminder_handle = ReminderHandle(asutils)
    scheduler_handle = ScheduleHandle(asutils)
    phnx = PhoenixAssistant(
        asutils,
        open_handler=opn,
        close_handler=clse,
        timer_handle=timer_handle,
        alarm_handle=alarm_handle,
        schedule_handle=scheduler_handle,
        reminder_handle=reminder_handle,
    )
    phnx.main_phnx()
