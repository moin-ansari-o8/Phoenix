# import win32gui
# import win32con
# import time


# def bring_window_to_foreground(window_title):
#     def enum_windows_callback(hwnd, extra):
#         if win32gui.IsWindowVisible(hwnd) and window_title in win32gui.GetWindowText(
#             hwnd
#         ):
#             extra.append(hwnd)

#     hwnd_list = []
#     win32gui.EnumWindows(enum_windows_callback, hwnd_list)

#     if hwnd_list:
#         hwnd = hwnd_list[0]
#         win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # Restore if minimized
#         win32gui.SetForegroundWindow(hwnd)  # Bring to foreground
#         print(f"Brought window to foreground: {win32gui.GetWindowText(hwnd)}")
#     else:
#         print(f"No window found with title containing: '{window_title}'")


# # Test the function
# time.sleep(5)
# bring_window_to_foreground(
#     "Arc"
# )  # Replace with the partial or full title of your window
# def square(x):
#     return x**2


# numbers = [1, 2, 3, 4]
# result = map(square, numbers)

# # `result` is a map object
# print(result)  # Output: <map object at 0x...>

# # Convert to list to view the results
# print(set(result))  # Output: [1, 4, 9, 16]
# query = "add schedule at 12:00 for Lunch"
# # queries = list(map(lambda x: x.lower().strip(), query.split("for")))
# queries = [q.lower().strip() for q in query.split("for")]
# print(queries)
# -----------------------------------------------------------------------------------------------
import json

file = r"E:\STDY\GIT_PROJECTS\Phoenix\data\intents.json"

with open(file, "r") as f:
    data = json.load(f)
    if not data.get("intents"):
        print("No intents found.")
    else:
        # Find tags with exactly one response and print "tag": "response"
        print("[")
        for entry in data["intents"]:
            if len(entry["responses"]) == 1:
                print(f'"{entry["tag"]}",')
        print("]")
