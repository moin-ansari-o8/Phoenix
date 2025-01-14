import sys
import json
import re
import random
import tkinter as tk
import datetime
from time import sleep
import pyautogui as pg
import subprocess
import keyboard
import webbrowser
import threading

import os
import pywhatkit as kit
from HelperPhoenix import SpeechEngine, VoiceAssistantGUI, VoiceRecognition, Utility


class PhoenixAssistant:

    def __init__(self, utility):
        self.AGREE = ["yes", "open", "yeah", "start", "launch"]
        current_dir = os.path.dirname(__file__)
        self.intents_file_path = os.path.join(current_dir, "data", "intents.json")
        self.intents = self.load_intents(self.intents_file_path)
        self.utility = utility
        self.tag_to_patterns = self.preprocess_patterns(self.intents)
        self.loop = False
        self.voice = False
        self.chat = False
        self.clear_terminal_thread = threading.Thread(
            target=self.clear_terminal_periodically, daemon=True
        )
        self.clear_terminal_thread.start()

    def execute_action(self, tag, query):
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
            "maximize": self.utility.maximize_window,
            "minimize": self.utility.minimize_window,
            "muteSpeaker": self.utility.mute_speaker,
            "newtab": self.utility.new_tab,
            "open": lambda query, response: self.utility.open_app(query, response),
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
            "setTimer": lambda x: self.utility.setTimer(x),
            # "viewTimer": self.utility.viewTimer(),
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
                "type_text",
                "setTimer",
            ]:
                action_map[tag](query)
            elif tag in ["open", "close", "select"]:
                action_map[tag](query, self.tag_response)
            elif tag in ["forward", "backward"]:
                action_map[tag](tag, query)
            else:
                action_map[tag]()

    def get_best_matching_intent(self, sent):
        """
        Find the best matching intent for the given sentence using the tag_to_patterns dictionary.

        Args:
            sent (str): The user input sentence.

        Returns:
            dict: A dictionary with the best matching tag and a response, or None if no match is found.
        """
        query_words = set(sent.lower().split())
        max_overlap = 0
        best_tag = None
        for tag, pattern_words in self.tag_to_patterns.items():
            overlap = len(query_words & pattern_words)
            if overlap > max_overlap:
                max_overlap = overlap
                best_tag = tag
        if best_tag:
            response = self.get_response(best_tag)
            return {"tag": best_tag, "response": response}
        return None

    def get_response(self, tag):
        for intent in self.intents:
            if intent["tag"] == tag:
                return random.choice(intent["responses"])

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
        while True:
            sent = input("Enter command: ").lower().strip()
            if "switch to voice" in sent:
                self.voice = True
                break
            if "phoenix" in sent and self.loop == False:
                sent = self.remove_phoenix_except_folder(sent)
                if sent:
                    self.handle_command(sent)
                    self.loop = True
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
            sent = self.takeCommand().lower().strip()
            if "switch to chat" in sent:
                self.chat = True
                break
            if "phoenix" in sent and self.loop == False:
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

    def clear_terminal_periodically(self):
        """
        Clears the terminal every 5 minutes.
        """
        os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal
        while True:
            sleep(300)  # Wait for 5 minutes
            os.system("cls" if os.name == "nt" else "clear")  # Clear the terminal

    def load_intents(self, file_path):
        with open(file_path, "r") as file:
            return json.load(file)["intents"]

    def main(self, sent):
        no_response_tag = [
            "addsong",
            "adjustBrightness",
            "afternoon",
            "backward",
            "battery",
            "close",
            "dateday",
            "dltsong",
            "evening",
            "forward",
            "fullscreen",
            "hide",
            "maximize",
            "minimize",
            "morning",
            "open",
            "pchibernate",
            "pcrestart",
            "pcshutdown",
            "pcsleep",
            "playpause",
            "playsong",
            "press",
            "random",
            "searchbrowser",
            "searchinsta",
            "searchyoutube",
            "select",
            "select",
            "setAlarm",
            "setReminder",
            "setReminder",
            "setTimer",
            "setfocus",
            "suggestsong",
            "suggestsong",
            "swtchTab",
            "time",
            "type",
            "whatis",
            "whois",
        ]
        query = self.remove_phoenix_except_folder(sent)
        matched_intent = self.get_best_matching_intent(query)
        if matched_intent:
            tag = matched_intent["tag"]
            print(tag)
            self.tag_response = matched_intent["response"]
            if tag not in no_response_tag:
                self.speak(self.tag_response)
            self.execute_action(tag, sent)
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
            tag = intent["tag"]
            patterns = intent["patterns"]
            word_set = set()
            for pattern in patterns:
                word_set.update(pattern.lower().split())
            tag_to_patterns[tag] = word_set
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
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    asutils = Utility(speech_engine, recognizer)
    # timer = TimerHandle()
    phnx = PhoenixAssistant(asutils)
    phnx.input_voice()
