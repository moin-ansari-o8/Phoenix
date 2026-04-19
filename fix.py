import uuid, os

with open(
    r"W:\workplace-1\Phoenix\utils\helpers\assistant_io.py", "r", encoding="utf-8"
) as f:
    lines = f.readlines()

new_lines = (
    lines[:212]
    + [
        "            if success and os.path.exists(unique_path):\n",
        "                import ctypes\n",
        "                winmm = ctypes.windll.winmm\n",
        '                alias = f"phoenix_{uuid.uuid4().hex[:8]}"\n',
        "                abs_path = os.path.abspath(unique_path)\n",
        '                winmm.mciSendStringW(f"close {alias}", None, 0, None)\n',
        '                winmm.mciSendStringW(f"open \\"{abs_path}\\" alias {alias}", None, 0, None)\n',
        '                winmm.mciSendStringW(f"play {alias} wait", None, 0, None)\n',
        '                winmm.mciSendStringW(f"close {alias}", None, 0, None)\n',
        "                try:\n",
        "                    os.remove(unique_path)\n",
        "                except:\n",
        "                    pass\n",
        "                return True\n",
        "            return False\n",
    ]
    + lines[235:]
)

with open(
    r"W:\workplace-1\Phoenix\utils\helpers\assistant_io.py", "w", encoding="utf-8"
) as f:
    f.writelines(new_lines)

print("done")
