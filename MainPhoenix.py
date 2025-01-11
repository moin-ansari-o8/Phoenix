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

    def speak(self, text):
        self.utility.speak(text)
    def takeCommand(self):
        return self.utility.take_command()
    def load_intents(self, file_path):
        with open(file_path, 'r') as file:
            return json.load(file)['intents']

    def match_pattern(self, sent, patterns):
        return sum([1 for pattern in patterns if pattern.lower() in sent.lower()])

    def get_response(self, tag):
        for intent in self.intents:
            if intent['tag'] == tag:
                return random.choice(intent["responses"])

    def input_chat(self):
        voice = False
        while True:
            sent = input("Enter command: ").lower()
            if "switch to voice" in sent:
                voice = True
                break
            elif sent:
                self.main(sent)
        if voice:
            self.input_voice()

    def input_voice(self):
        while True:
            sent = self.takeCommand().lower().strip()
            if "phoenix" in sent:
                sent = re.sub(r'phoenix', '', sent, flags=re.IGNORECASE).strip()
                if sent:
                    for part in sent.split(" and "):
                        if part:
                            self.main(part)
                            sleep(1)

    def main(self, sent):
        no_response_tag = [
            "morning", "afternoon", "evening", "pcrestart", "pcshutdown", "pchibernate",
            "pcsleep", "open", "close", "time", "battery", "dateday", "searchinsta",
            "searchbrowser", "searchyoutube", "swtchTab", "select", "playpause", "press",
            "setReminder", "type", "random", "suggestsong", "maximize", "minimize", "fullscreen",
            "adjustBrightness", "hide", "whatis", "whois", "select", "setfocus", "forward", "backward"
        ]
        query = re.sub(r'\bphoenix\b', '', sent, flags=re.IGNORECASE).strip()

        # Find matching intent
        matched_intent = self.get_best_matching_intent(sent)
        
        if matched_intent:
            tag = matched_intent["tag"]
            if tag not in no_response_tag:
                self.speak(matched_intent["response"])
            self.execute_action(tag)

    def get_best_matching_intent(self, sent):
        max_count = 0
        best_response = None
        for intent in self.intents:
            count = self.match_pattern(sent, intent['patterns'])
            if count > max_count:
                max_count = count
                best_response = {"tag": intent["tag"], "response": random.choice(intent["responses"])}
        return best_response

    def execute_action(self, tag):
        action_map = {
            "pcshutdown": self.utility.shutD,
            "pcrestart": self.utility.restarT,
            "pcsleep": self.utility.sleeP,
            "pchibernate": self.utility.hibernatE,
            "muteSpeaker": self.utility.mute_speaker
        }
        if tag in action_map:
            action_map[tag]()
            if tag == "pcsleep":
                self.speak(self.utility.onL())
            if tag == "pchibernate":
                sleep(40)
                self.utility.restart_explorer()
                self.speak(self.utility.onL())

if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    asutils = Utility(speech_engine, recognizer)
    phnx = PhoenixAssistant(asutils)
    phnx.input_voice()
