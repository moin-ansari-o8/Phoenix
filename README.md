# Phoenix

A Desktop Assistant

You may/may not find this program full of hard coded. If you are interested to know how this Phoenix works than make it yours, and solve the errors and the hard coded programs.

## Flow of the Phoenix

1. load.py :: starts all necessary py files for the phoenix to run perfectly. (bgprogs/BgBtryPHNX.pyw,bgprogs/BgTmPHNX.pyw,MainPHNX.py)

2. bgprogs/BgBtryPHNX.pyw,bgprogs/BgTmPHNX.pyw :: just background programs that keeps track of the battery percentage and time related functions.(keeps checking the time for alarm,reminder etc)

3. MainPHNX.py :: this is the main program which always listen to you and replies to the user as per user queries.

4. data/intents.json :: i have added some tags(intent tracker of user) in here, MainPHNX listens the query it comes here and replies to the user if the the query is conversation based else in the MainPHNX there is function _execute_action which handles other functionalities which needs the help of libraries which are defined in the helpers/UtilitiesPHNX.py (what is time/wheather/date? etc)

try and explore rest of the code by urself.

## Install Dependencies

Run the following command to install all the required dependencies:

```bash
pip install -r requirements.txt
```

## Do this to run

- for just listening and all run only MainPHNX.py
- for running the whole phoenix with bg battery checking and time related all methods run load.py .

## Future Enhancements

- Implement a more intuitive and user-friendly GUI.
- Add Reinforcement learning algorithm.

## Contribute

We welcome contributions from the community. Here are some ways you can help:

1. **Report Bugs**: If you find a bug, please report it by creating an issue on GitHub.

2. **Suggest Features**: If you have an idea for a new feature, please open an issue to discuss it.

3. **Submit Pull Requests**: If you have a fix or a new feature, please submit a pull request. Make sure to follow the contribution guidelines.

4. **Improve Documentation**: Help us improve our documentation by making it clearer and more comprehensive.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details .
