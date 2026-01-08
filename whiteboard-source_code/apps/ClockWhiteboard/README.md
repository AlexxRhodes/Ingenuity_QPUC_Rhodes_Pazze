# ClockWhiteboard

This is a simple app that shows the current time on the whiteboard and refreshes it every second.
It is intended as an example (in python) of an agent using services and replies to communicate with the Whiteboard.

## Prerequisites

- Python3 (https://www.python.org/downloads/)
- Ingescape python binding (from pip)

## Install dependencies

A requirements.txt is provided. Install dependencies using pip

```bash
pip install -r requirements.txt
```

## Run

You can pass arguments to the main script to configure your agent.

```bash
python3 src/main.py --device en0 --port 5670
```

Some parameters are optional, others are mandatory. Use `--help` to learn more.
