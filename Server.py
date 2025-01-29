# websocket_server.py
import asyncio
import websockets
import json
from helpers.UtilitiesPHNX import Utility, CloseAppHandler, OpenAppHandler
from helpers.HelperPHNX import VoiceAssistantGUI, VoiceRecognition, SpeechEngine
from helpers.TimeBasedHandlePHNX import (
    TimerHandle,
    AlarmHandle,
    ReminderHandle,
    ScheduleHandle,
)
from MainPHNX import PhoenixAssistant
import tkinter as tk


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

    async def websocket_server(websocket, phnx):  # Add 'phnx' parameter
        async for message in websocket:
            data = json.loads(message)
            user_prompt = data.get("user_prompt", "")
            print(f"Received: {user_prompt}")
            response = phnx.process_input(user_prompt)
            print("Sending: ", response)

            # Send response back to the client
            await websocket.send(json.dumps({"ai_prompt": response}))

    async def start_server(phnx):  # Add 'phnx' parameter
        async with websockets.serve(
            lambda ws: websocket_server(ws, phnx), "127.0.0.1", 8765
        ):
            print("WebSocket server started on ws://127.0.0.1:8765")
            await asyncio.Future()  # Run forever

    asyncio.run(start_server(phnx))
