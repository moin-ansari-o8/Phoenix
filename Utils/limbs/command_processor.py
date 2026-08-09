"""
Processor Helper for Phoenix - Intent Matching and Action Execution
Extracted from main_assistant.py for background voice processor
"""

import json
import re
import random
import os


class PhoenixAssistant:
    """Intent matcher and action executor for voice commands"""

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
        self.AGREE = [
            "yes",
            "open",
            "yeah",
            "start",
            "launch",
            "han",
            "ya",
            "sure",
            "ok",
            "please",
            "yes sir",
            "yes please",
            "yes madam",
            "yes ma'am",
        ]
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
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
        self.reload = False
        self.last_tag_response = ""
        
        from core.config import AppConfig
        from Utils.ai_manager import AIDecisionMaker
        from Utils.limbs.intent_router import IntentRouter
        from Utils.limbs.memory_manager import (
            ConversationContext,
            RememberStore,
            load_soul,
        )

        self.ai_manager = AIDecisionMaker()
        self.soul = load_soul()
        self.remember_store = RememberStore(
            max_entries=AppConfig.memory["max_remember_entries"]
        )
        self.context = ConversationContext(
            max_turns=AppConfig.memory["context_turns"]
        )
        self.router = IntentRouter(
            self.intents,
            self.ai_manager,
            assistant=self,
            soul=self.soul,
            context=self.context,
            remember_store=self.remember_store,
        )

    def _execute_action(self, tag, query):
        common_tags = {
            self.utility.handle_time_based_greeting: (
                "morning",
                "afternoon",
                "evening",
            ),
            # "whatis"/"whois" deliberately NOT mapped here: those are questions
            # and must be answered in chat by the router, never by opening a
            # browser tab. handle_whatis_whois remains available for an explicit
            # "search google for X" intent if one is added later.
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
                try:
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
                except Exception as e:
                    error_msg = f"Error executing action '{tag}': {e}"
                    print(error_msg)
                    try:
                        self.utility.speak(
                            f"Sorry, I encountered an error performing that action."
                        )
                    except:
                        pass
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
            "extra setup": self.utility.extra_desk_setup,
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
            "trash setup": self.utility.setup_trash,
            "alpha setup": self.utility.setup_alpha,
            "study setup": self.utility.setup_study,
            "folder structure generate": self.utility.folder_structure_generate,
            "movewind": lambda x: self.utility.process_move_window(x),
            "switchdesk": lambda x: self.utility.switch_desk(x),
            "play-game": lambda x: self.utility.switch_desk(x),
            "knock-knock": self.utility.knock_knock,
            "focus-phnx": self.utility.focus_phnx,
        }
        if tag in action_map:
            try:
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
            except Exception as e:
                error_msg = f"Error executing action '{tag}': {e}"
                print(error_msg)
                try:
                    self.utility.speak(
                        f"Sorry, I encountered an error performing that action."
                    )
                except:
                    pass

    def _get_response(self, tag):
        for intent in self.intents:
            if intent["tag"] == tag:
                return random.choice(intent["responses"])

    def load_intents(self, file_path):
        with open(file_path, "r") as file:
            return json.load(file)["intents"]

    def hib_phnx(self):
        self.voice = False

    def main(self, sent):
        """Main processing method - matches intent and executes action"""
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
            "folder structure generate",
        ]

        query_main = self.remove_phoenix_except_folder(sent)
        query = self.remove_phoenix_except_folder(sent)
        keywords = ["open", "launch", "start"]
        for keyword in keywords:
            if keyword in query and "restart" not in query:
                self.opn.process_query(query, self.mQuery)
                return True  # Open handler matched
        if "close" in query:
            self.clse.process_query(query, self.mQuery)
            return True  # Close handler matched
        match = re.search(r"play (.+?) song", query)
        if match:
            query = re.sub(r"play .+? (song|music)", "play {this} song", query)
        result = self.router.route(query)

        if result.source == "fastpath-grammar":
            # The grammar already executed the action; the utility speaks itself.
            pass
        elif result.source == "fastpath":
            tag = result.tag
            self.tag_response = result.spoken or ""
            if tag not in no_response_tag and self.tag_response:
                self.speak(self.tag_response)
                self.last_tag_response = self.tag_response
            self._execute_action(tag, query_main)
            self.context.add(query_main, self.tag_response)
        elif result.spoken:
            # AI-composed answer, or a model-unreachable notice.
            self.speak(result.spoken)
        # result.source == "tool" means the action already ran and spoke itself.

        self.loop = True
        return True

    def preprocess_patterns(self, intents):
        """
        Process intents JSON data to create a dictionary mapping tags to sets of unique pattern words.
        """
        tag_to_patterns = {}
        for intent in intents:
            tag_to_patterns[intent["tag"]] = intent["patterns"]
        return tag_to_patterns

    def remove_phoenix_except_folder(self, sent):
        """
        Remove Phoenix wake-word variants except when used as 'phoenix folder'.
        """
        aliases_pattern = r"phoenix|phoenim|phonix|phoneix|fenix|pheonix"
        sent = re.sub(
            rf"(?<!\\w)({aliases_pattern})(?! folder)(?!\\w)",
            "",
            sent,
            flags=re.IGNORECASE,
        ).strip()
        return sent

    def speak(self, text, speed=174):
        self.utility.speak(text, speed)

    def process_input(self, query):
        return self.main(query)
