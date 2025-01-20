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
        self.voice = False
        self.chat = False
        self.opn = open_handler
        self.clse = close_handler
        self.cls_print = True

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
        }
        for func, tags in common_tags.items():
            if tag in tags:
                if func == self.utility.sleep_phnx:
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
            "press": self.utility.press_key,
            "saytime": self.utility.tim,
            "screenshot": self.utility.screenshot,
            "searchbrowser": self.utility.search_browser,
            "searchinsta": self.utility.search_instagram,
            "searchyoutube": self.utility.search_youtube,
            "select": lambda query, response: self.utility.select_action(
                query, response
            ),
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

    def _get_best_matching_intenty(self, sent):
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
        "\n        Find the best matching intent for a given sentence based on the highest similarity probability.\n        "
        best_tag, highest_probability = max(
            (
                (tag, self._getSentProbability(sent, patterns))
                for tag, patterns in self.tag_to_patterns.items()
            ),
            key=lambda x: x[1],
            default=(None, 0),
        )

        if (
            best_tag == "openelse"
            or best_tag == "playsong"
            or best_tag == "setTimer"
            or best_tag == "setAlarm"
            or best_tag == "setReminder"
            or best_tag == "dltReminder"
            or highest_probability > 80
        ):
            response = self._get_response(best_tag)
            return {"tag": best_tag, "response": response}

        return None

    def _get_response(self, tag):
        for intent in self.intents:
            if intent["tag"] == tag:
                return random.choice(intent["responses"])

    def print_phoenix(self):
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
        print(" ", "=" * (terminal_width - 2))

    def check_cls_phnx(self):
        self.cls_print = False
        sleep(65)
        self.cls_print = True
        return

    def cls_phnx(self):
        """
        Clears the terminal every 5 minutes.
        """
        os.system("cls" if os.name == "nt" else "clear")
        self.print_phoenix()
        return True

    def handle_command(self, sent):
        if sent:
            parts = [part.strip() for part in sent.split(" and ")]
            for part in parts:
                if part:
                    self.main(part)
        else:
            self.loop = False

    def input_chat(self):
        self.voice = False
        self.loop = False
        while True:
            sent = input("Enter command: ").lower().strip()
            if "switch to voice" in sent:
                self.voice = True
                break
            if (
                "phoenix" in sent
                or "finish" in sent
                or "feelings" in sent
                or "feeling" in sent
            ) and self.loop == False:
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
        if self.voice:
            self.input_voice()

    def input_voice(self):
        self.chat = False
        self.loop = False
        while True:
            if self.cls_print:
                if self.cls_phnx():
                    self.check_cls_phnx_thread = threading.Thread(
                        target=self.check_cls_phnx, daemon=True
                    )
                    self.check_cls_phnx_thread.start()
            sent = self.takeCommand().lower().strip()
            if "switch to chat" in sent:
                self.chat = True
                break
            if (
                "phoenix" in sent
                or "finish" in sent
                or "feelings" in sent
                or "feeling" in sent
            ) and self.loop == False:
                self.mQuery = sent
                sent = self.remove_phoenix_except_folder(sent)
                if sent:
                    self.handle_command(sent)
            elif self.loop == True:
                self.handle_command(sent)
            elif not sent:
                self.loop = False
            else:
                self.loop = False
        if self.chat:
            self.input_chat()

    def load_intents(self, file_path):
        with open(file_path, "r") as file:
            return json.load(file)["intents"]

    def main(self, sent):
        no_response_tag = [
            "add",
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
            "select",
            "setAlarm",
            "setReminder",
            "setTimer",
            "sub",
            "suggestsong",
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
        matched_intent = self._get_best_matching_intenty(query)
        if matched_intent:
            # print(f" : {query_main}")        ##will have to make a log file for it to print the user input and to store it in log file
            tag = matched_intent["tag"]
            print(f"# : {self.mQuery}\n")
            self.tag_response = matched_intent["response"]
            if tag not in no_response_tag:
                self.speak(self.tag_response)
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

    def speak(self, text):
        self.utility.speak(text)

    def takeCommand(self):
        return self.utility.take_command()


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
    phnx.input_voice()
