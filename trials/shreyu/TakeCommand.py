import speech_recognition as sr


class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def takeCommand(self):
        """
        Listens to the user's voice input, prints what was understood,
        and displays a list of possible variations.
        """
        try:
            print(">>>", end="\r")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source)

            print("<<<", end="\r")
            # Use Google Speech Recognition to process the audio
            user_input = self.recognizer.recognize_google(audio)
            print(f"You said: {user_input}")

            # Generate possible variations using recognizer alternatives
            try:
                alternatives = self.recognizer.recognize_google(audio, show_all=True)
                if isinstance(alternatives, dict) and "alternative" in alternatives:
                    print("\nHere are the variations the program considered:")
                    for i, option in enumerate(alternatives["alternative"], 1):
                        print(f"{i}. {option.get('transcript', 'N/A')}")
                else:
                    print("No alternative transcripts available.")
            except Exception as e:
                print("Unable to fetch alternative transcripts:", str(e))

        except sr.UnknownValueError:
            print("<!>", end="\r")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
        except Exception as e:
            print(f"An error occurred: {e}")


# Example Usage
if __name__ == "__main__":
    assistant = VoiceAssistant()
    print(">>> : u can say")
    print("<<< : processing what u said")
    print("<!> : didn't understood what u say or blank")
    while True:
        assistant.takeCommand()
