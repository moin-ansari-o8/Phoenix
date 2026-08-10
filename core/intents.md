# Decision Rules

> **IMPORTANT — how this file is used.** Only the block between the
> `PROMPT:BEGIN` / `PROMPT:END` markers is sent to the model on each decision.
> Everything after it is documentation for you, and reference for the
> deterministic matchers in `Utils/limbs/intent_router.py`.
>
> **Keep the prompt block small.** Measured on this machine: a 7,100-character
> prompt cost 13.1-13.6s per decision and routed "increase brightness by 30%"
> wrongly; ~1,000 characters gave 1.5-3.0s and routed it correctly. A long prompt
> also dilutes the decision. Add detail to the reference tables below, NOT to the
> prompt block.
>
> **But prompt size is the second-order effect.** The first-order cost is whether
> the model fits in VRAM. This machine has a GTX 1650 with 4GB: `gemma3` (4.4GB
> loaded) runs 45% on CPU and answers in 8-16s, while `llama3.2:latest` (3.1GB)
> runs 90% on GPU and answers in 1-3s. If latency is bad, check
> `ollama ps` for the CPU/GPU split BEFORE editing this file.

<!-- PROMPT:BEGIN -->
Pick exactly ONE tool for the user's message.
Reply with ONLY JSON: {"tool":"...","arg":"...","extra":"..."}

Tools:
- get_device_state - a live reading from THIS pc. arg = time|date|battery|weather|timers|alarms|reminders|songs
- control_device - change a pc setting. arg = action tag, extra = target
- remember - the user stated a personal fact. arg = fact in third person, extra = People|Preferences|Facts|Projects
- search_web - look it up online. arg = query
- answer_directly - answer from what you already know

Rules, in order:
1. User is TELLING you something personal, not asking: "my friend Moin told
   me...", "i prefer dark mode", "i work at X" -> remember. If it is a QUESTION
   ("who is my friend?") use answer_directly instead. Never look up a person the
   user calls their own. Greetings and pleasantries ("hi", "thanks", "ok") are
   NOT facts - they are answer_directly. Neither is a REQUEST: "a joke on X",
   "tell me a story", "write a poem" are answer_directly.
   Asking you to FORGET something is also remember (it is handled as a delete).
2. Wants a live reading off this pc (clock, date, battery, local weather, their
   timers/alarms/reminders/songs) -> get_device_state, even if phrased as a
   question.
3. Tells you to change something on the pc -> control_device.
4. Otherwise it is a knowledge question. **answer_directly is the DEFAULT.**
   Use search_web ONLY when the answer genuinely changes over time - you need a
   positive reason. Those reasons are: population, prices, exchange rates,
   news, sports scores, who currently holds an office, latest software
   versions, or the words today/now/current/latest/recent appear.
   Everything else is answer_directly, including capitals, history, geography,
   definitions, science, maths, who I am, who the user is, their friends, word
   meanings and chit-chat. "capital of france" is Paris - you know it, do not
   search. If you cannot decide, use answer_directly.
<!-- PROMPT:END -->

---

# Reference (not sent to the model)

## How to decide

1. **Where does the answer live?**
   - On this PC right now (clock, date, battery, weather, timers, alarms, reminders,
     songs) -> `get_device_state`
   - In something the user already told me, or in who I am / who they are ->
     `answer_directly`
   - In public world knowledge about a named person, place or company ->
     `lookup_encyclopedia`
   - In today's news, prices, scores, or anything that changes fast -> `search_web`
2. **Is the user telling me to change something on the PC?** -> `control_device`

If the user is stating a personal fact rather than asking anything -> `remember`.

---

## get_device_state

Read a live value from this PC. `arg` must be one of:
`time`, `date`, `battery`, `weather`, `timers`, `alarms`, `reminders`, `songs`

Use when the user wants the CURRENT value.

| Message | arg |
|---|---|
| what is the time / whats the time / time please | time |
| what is today / what day is it / todays date | date |
| how much battery / am i charging / battery percent | battery |
| whats the weather / is it going to rain | weather |
| do i have any timers / show my timers | timers |
| what alarms do i have | alarms |
| what are my reminders | reminders |
| list my songs / what songs do i have | songs |

**Do NOT use this when:**
- The user asks what a word MEANS. "what do you mean by time" is `answer_directly`.
- The subject is not one of the eight values above. "tell me the capital of France"
  has nothing to do with the clock -> `lookup_encyclopedia`.

---

## control_device

Change something on this PC. `arg` is the action, `extra` is the target.

`arg` must be one of:
`open`, `close`, `openelse`, `playsong`, `playpause`, `adjustVolume`,
`adjustBrightness`, `muteSpeaker`, `unmuteSpeaker`, `screenshot`, `setTimer`,
`setAlarm`, `dltAlarm`, `setReminder`, `newtab`, `closetab`, `changetab`,
`swtchTab`, `maximize`, `minimize`, `fullscreen`, `hide`, `pcshutdown`,
`pcrestart`, `pcsleep`, `pchibernate`, `phnxrestart`, `bluetooth`, `hotspot`,
`switchdesk`, `movewind`, `press`, `type`, `searchyoutube`, `searchinsta`,
`amazon`, `flipkart`, `suggestsong`, `addsong`, `dltsong`, `knock-knock`

| Message | arg | extra |
|---|---|---|
| open brave / launch chrome | open | brave |
| close spotify | close | spotify |
| increase the brightness / brightness up | adjustBrightness | increase |
| decrease brightness / dim the screen / lower brightness | adjustBrightness | decrease |
| set brightness to 50 | adjustBrightness | 50 |
| turn up the volume / volume up / louder | adjustVolume | increase |
| turn it down / volume down / quieter | adjustVolume | decrease |
| set volume to 30 | adjustVolume | 30 |
| mute / mute the speaker | muteSpeaker | |
| unmute | unmuteSpeaker | |
| take a screenshot | screenshot | |
| set a timer for ten minutes | setTimer | ten minutes |
| set an alarm for 7 am | setAlarm | 7 am |
| remind me to call mom at 6 | setReminder | call mom at 6 |
| play some music / play a song | playsong | |
| pause / resume / play pause | playpause | |
| shut down the pc | pcshutdown | |
| restart the pc | pcrestart | |
| restart phoenix / restart yourself | phnxrestart | |
| toggle bluetooth | bluetooth | |
| turn on hotspot | hotspot | |
| maximize / minimize / fullscreen | maximize | |
| new tab / close tab | newtab | |
| search youtube for lofi | searchyoutube | lofi |
| search amazon for headphones | amazon | headphones |
| tell me a joke / knock knock | knock-knock | |

**Do NOT use this to answer a question.** "how much battery" is a reading, not a change.

---

## answer_directly

Answer from who I am, who the user is, what they have told me before, the recent
conversation, or my own general knowledge. No lookup, no PC action.

**ALWAYS use this for:**
- Questions about ME: my name, who made me, who my creator or master is, what I can do.
- Questions about THE USER: who am I, what is my name, what do I like, what do I do.
- Questions about people in the user's life: their friends, family, colleagues.
  Those facts are in my memory, not on the internet.
- The meaning of an ordinary word or everyday concept.
- Greetings, thanks, chit-chat, opinions, follow-ups to the last thing said.

| Message | why |
|---|---|
| who are you / whats your name | about me |
| who made you / who is your creator / who is your master | about me - the developer |
| who is kaly | that is the user, my developer - about them |
| who am i / whats my name | about the user |
| who is my friend / whats my friends name | in my memory |
| what do you mean by time | meaning of a word |
| what is artificial intelligence | general concept i know |
| hello / thanks / how are you | chit-chat |
| tell me more / go on | follow-up to the last answer |

**Never search the web for who I am, who made me, or who the user is.**

---

## lookup_encyclopedia

Look up a FAMOUS, PUBLIC person, place, company or organisation - something with a
Wikipedia article. `arg` is the subject name, cleaned up.

| Message | arg |
|---|---|
| who is salman khan | Salman Khan |
| what is openai / what does open ai do | OpenAI |
| what is anthropic / what does anthropic do | Anthropic |
| where is mount everest | Mount Everest |
| what is isro | ISRO |

**Do NOT use this for:** the user's own friends or family, the user themselves, me,
the meaning of a common word, or **any fact that never changes** — a capital city,
a historical date, a scientific constant. Those go to `answer_directly`; looking
them up wastes 5-10 seconds for an answer the model already has.

## Volatility — the general vs realtime split

The single most useful question: **would this answer be different next year?**

| Message | Tool | Why |
|---|---|---|
| what is the capital of france | answer_directly | Paris. Never changes. |
| what is the population of france | search_web | changes every year |
| who was mahatma gandhi | answer_directly | history, fixed |
| who is the current pm of india | search_web | changes with elections |
| what is python | answer_directly | a definition |
| what is the latest python version | search_web | changes with releases |
| how far is the moon | answer_directly | a constant |
| what is the price of bitcoin | search_web | changes by the minute |
| who is salman khan | lookup_encyclopedia | stable, but details worth checking |
| what is 15 percent of 240 | answer_directly | maths, no lookup |

---

## search_web

Search the internet. `arg` is the search query. Use for anything that changes fast
or that I cannot be confident about.

| Message | arg |
|---|---|
| latest news about isro | latest ISRO news |
| what is the price of bitcoin | bitcoin price today |
| who won the match last night | latest match result |
| is there a new iphone | newest iPhone model |

---

## remember

The user stated a durable personal fact instead of asking something.
`arg` is the fact written in third person. `extra` is one of:
`People`, `Preferences`, `Facts`, `Projects`

| Message | arg | extra |
|---|---|---|
| my friend moin told me about this | Moin is a friend of the user | People |
| my sister is priya | Priya is the user's sister | People |
| i prefer dark mode | The user prefers dark mode | Preferences |
| i hate popup notifications | The user dislikes popup notifications | Preferences |
| i work at magnetar | The user works at Magnetar | Facts |
| im building a django app called dukan | The user is building a Django app called Dukan | Projects |

**Do NOT use this for questions.** "who is my friend" is `answer_directly`.
