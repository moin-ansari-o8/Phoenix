# Phoenix

A Desktop Assistant

You may/may not find this program full of hard coded. If you are interested to know how this Phoenix works than make it yours, and solve the errors and the hard coded programs.

## Flow of the Phoenix

1. load.py :: starts all necessary py files for the phoenix to run perfectly. (bgprogs/BgBtryPHNX.pyw,bgprogs/BgTmPHNX.pyw,MainPHNX.py)

2. bgprogs/BgBtryPHNX.pyw,bgprogs/BgTmPHNX.pyw :: just background programs that keeps track of the battery percentage and time related functions.(keeps checking the time for alarm,reminder etc)

3. MainPHNX.py :: this is the main program which always listen to you and replies to the user as per user queries.

4. data/intents.json :: i have added some tags(intent tracker of user) in here, MainPHNX listens the query it comes here and replies to the user if the the query is conversation based else in the MainPHNX there is function _execute_action which handles other functionalities which needs the help of libraries which are defined in the helpers/UtilitiesPHNX.py (what is time/wheather/date? etc)

try and explore rest of the code by urself.
discord for more details : [discord](https://discord.gg/txYCt2FM)

## Install Dependencies

Run the following command to install all the required dependencies:

```bash
pip install -r requirements.txt
```

## Future Enhancements

- Implement a more intuitive and user-friendly GUI.
- Add Reinforcement learning algorithm.
