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
        self.tag_to_patterns = self.preprocess_patterns(self.intents)  # Generate tag-to-pattern mapping
        self.loop = False
        self.voice = False
        self.chat = False

    def speak(self, text):
        self.utility.speak(text)

    def takeCommand(self):
        return self.utility.take_command()

    def load_intents(self, file_path):
        with open(file_path, 'r') as file:
            return json.load(file)['intents']

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
            
            # Create a set of unique words from all patterns for the tag
            word_set = set()
            for pattern in patterns:
                word_set.update(pattern.lower().split())  # Split pattern into words and add to set
            
            tag_to_patterns[tag] = word_set

        return tag_to_patterns

    def get_best_matching_intent(self, sent):
        """
        Find the best matching intent for the given sentence using the tag_to_patterns dictionary.

        Args:
            sent (str): The user input sentence.

        Returns:
            dict: A dictionary with the best matching tag and a response, or None if no match is found.
        """
        query_words = set(sent.lower().split())  # Break query into a set of words
        max_overlap = 0
        best_tag = None

        for tag, pattern_words in self.tag_to_patterns.items():
            overlap = len(query_words & pattern_words)  # Calculate word overlap
            if overlap > max_overlap:
                max_overlap = overlap
                best_tag = tag

        if best_tag:
            response = self.get_response(best_tag)
            return {"tag": best_tag, "response": response}
        
        return None

    def get_response(self, tag):
        for intent in self.intents:
            if intent['tag'] == tag:
                return random.choice(intent["responses"])

    def input_chat(self):
        self.voice=False
        while True:
            sent = input("Enter command: ").lower().strip()
            if "switch to voice" in sent:
                self.voice = True
                break
            if "phoenix" in sent and self.loop==False:
                sent = self.remove_phoenix_except_folder(sent)
                if sent:
                    self.handle_command(sent)
                    self.loop=True
            elif self.loop==True:
                self.handle_command(sent)
            elif not sent:
                self.loop=False
            else:
                self.loop=False
                
        if self.voice:
            self.input_voice()

    def input_voice(self):
        self.chat=False
        while True:
            sent = self.takeCommand().lower().strip()
            if "switch to chat" in sent:
                self.chat = True
                break
            if ("phoenix" in sent or "finish" in sent) and self.loop==False:
                sent = self.remove_phoenix_except_folder(sent)
                if sent:
                    self.handle_command(sent)
                    self.loop=True
            elif self.loop==True:
                self.handle_command(sent)
            elif not sent:
                self.loop=False
            else:
                self.loop=False
                
        if self.chat:
            self.input_chat()
                
    def handle_command(self, sent):
        if sent:
            # Split the sentence based on 'and' and strip extra spaces
            parts = [part.strip() for part in sent.split(" and ")]
            # Iterate through all parts and pass each to the main function
            for part in parts:
                if part:  # Ensure non-empty strings are passed
                    self.main(part)              

    def remove_phoenix_except_folder(self, sent):
        """
        Remove 'phoenix' from the string except when it's part of folder name like 'phoenix folder'.
        """
        # Regex to keep 'phoenix folder' intact
        sent = re.sub(r'(?<!\w)phoenix(?! folder)(?!\w)', '', sent, flags=re.IGNORECASE).strip()
        return sent

    def main(self, sent):
        no_response_tag = [
            "morning", "afternoon", "evening", "pcrestart", "pcshutdown", "pchibernate",
            "pcsleep", "open", "close", "time", "battery", "dateday", "searchinsta",
            "searchbrowser", "searchyoutube", "swtchTab", "select", "playpause", "press",
            "setReminder", "type", "random", "suggestsong", "maximize", "minimize", "fullscreen",
            "adjustBrightness", "hide", "whatis", "whois", "select", "setfocus", "forward", "backward"
        ]
        
        query = self.remove_phoenix_except_folder(sent)  # Remove phoenix keyword
        # Find matching intent
        matched_intent = self.get_best_matching_intent(query)
        
        if matched_intent:
            tag = matched_intent["tag"]
            print(tag)
            self.tag_response = matched_intent["response"]
            if tag not in no_response_tag:
                self.speak(self.tag_response)
            self.execute_action(tag, sent)
            self.loop=True
        else:
            # self.speak("Sorry, I didn't get that.")
            self.loop=False
            

    def execute_action(self, tag, query):
        common_tags = {
            self.utility.handle_time_based_greeting: ("morning", "afternoon", "evening"),
            self.utility.sleep_phnx: ("sleepbye", "donotlisten"),
            self.utility.handle_whatis_whois: ("whatis", "whois"),
            self.utility.perform_window_action: ("hide", "minimize", "maximize", "fullscreen"),
            self.utility.move_direction: ("forward", "backward"),
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
                    func(tag, self.response)  
                return
        
        action_map = {
            "pcshutdown": self.utility.shutD,
            "pcrestart": self.utility.restarT,
            "pcsleep": self.utility.sleeP,
            "pchibernate": self.utility.hibernatE,
            "muteSpeaker": self.utility.mute_speaker,
            "unmuteSpeaker": self.utility.unmute_speaker,
            "battery": self.utility.battery_check,
            "dateday": self.utility.date_day,
            "adjustVolume": lambda query: self.utility.adjust_volume(query),  # Use lambda to pass arguments
            "adjustBrightness": lambda query: self.utility.adjust_brightness(query), 
            "changetab": lambda query: self.utility.change_tab(query), 
            "open": lambda query, response: self.utility.open_app(query, response), 
            "close": lambda query, response: self.utility.close_app(query, response), 
            "select": lambda query, response: self.utility.select_action(query, response),
            "phnxrestart": self.utility.restart_phoenix,
            "screenshot": self.utility.screenshot,
            "hotspot": self.utility.hotspot,
            "bluetooth": self.utility.bluetooth,
            "newtab": self.utility.new_tab,
            "closetab": self.utility.close_tab,
            "saytime": self.utility.tim,
            "searchinsta": self.utility.search_instagram,
            "searchbrowser": self.utility.search_browser,
            "setfocus": self.utility.set_focus,
            "searchyoutube": self.utility.search_youtube,
            "hide": self.utility.hide_window,
            "press": self.utility.press_key,
            "minimize": self.utility.minimize_window,
            "maximize": self.utility.maximize_window,
            "fullscreen": self.utility.toggle_fullscreen,
            "type": lambda query: self.utility.type_text(query),
            "swtchTab": self.utility.switch_tab,
            "playpause": lambda query: self.utility.play_pause_action(query),
            "dltsong": self.utility.delete_song,
            "suggestsong": self.utility.suggest_song,
            "playsong": self.utility.play_random_song,
            "addsong": self.utility.add_song,
            "viewsongs": self.utility.view_songs,
            "setTimer": self.utility.set_timer
        }
        
        if tag in action_map:  # for single argument (query)
            if tag in ["adjustVolume", "adjustBrightness", "changetab", "whatis", "whois", "type_text"]:
                action_map[tag](query)
            elif tag in ["open", "close", "select"]:  # for two arguments (query, response)
                action_map[tag](query, self.tag_response)
            elif tag in ["forward", "backward"]:
                action_map[tag](tag, query)
            else:
                action_map[tag]()

if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    asutils = Utility(speech_engine, recognizer)
    phnx = PhoenixAssistant(asutils)
    phnx.input_chat()
