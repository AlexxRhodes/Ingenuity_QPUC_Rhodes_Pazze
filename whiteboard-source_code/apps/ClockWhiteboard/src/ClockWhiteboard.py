#!/usr/bin/env -P /usr/bin:/usr/local/bin python3 -B
# coding: utf-8

#
#  ClockWhiteboard.py
#  ClockWhiteboard
#  Created by Ingenuity I/O on 2025/11/28
#
# "no description"
#
import datetime
from math import floor
import ingescape as igs


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


TEXT_TOKEN = "TEXT_TOKEN"

class ClockWhiteboard(metaclass=Singleton):
    def __init__(self):
        # inputs
        self._Time_IsoI = None
        self._TimestampI = None

        # outputs
        self._Time_IsoO = None
        self._TimestampO = None

        # BEGIN user code
        self._current_time = datetime.datetime.now()
        self.clean_ids()
        # END user code

    def clean_ids(self):
        self.text_id = None

    def timer_timeout(self):
        time_str = "OUTATIME"
        if self._current_time is None:
            self._current_time = datetime.datetime.now()

        time_str = self._current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.Time_IsoO = time_str
        self.TimestampO = floor(self._current_time.timestamp())

        if self.text_id is None:
            igs.service_call("Whiteboard", "addText", (time_str, 160.0, 0.0, "orange"), TEXT_TOKEN)
        else:
            igs.service_call("Whiteboard", "setStringProperty", (self.text_id, "text", time_str), None)

        self._current_time = self._current_time + datetime.timedelta(seconds=1)


    # inputs
    @property
    def Time_IsoI(self):
        return self.Time_IsoI

    @Time_IsoI.setter
    def Time_IsoI(self, value):
        self._Time_IsoO = value
        try:
            self._current_time = datetime.datetime.fromisoformat(value)
        except Exception as e:
            igs.error(f"Received time string cannot be parsed {str(e)}")

    @property
    def TimestampI(self):
        return self.TimestampI

    @TimestampI.setter
    def TimestampI(self, value):
        self._TimestampO = value
        try:
            self._current_time = datetime.datetime.fromtimestamp(value)
        except Exception as e:
            igs.error(f"Received timestamp cannot be parsed {str(e)}")

    # outputs
    @property
    def Time_IsoO(self):
        return self._Time_IsoO

    @Time_IsoO.setter
    def Time_IsoO(self, value):
        self._Time_IsoO = value
        if self._Time_IsoO is not None:
            igs.output_set_string("time_iso", self._Time_IsoO)

    @property
    def TimestampO(self):
        return self._TimestampO

    @TimestampO.setter
    def TimestampO(self, value):
        self._TimestampO = value
        if self._TimestampO is not None:
            igs.output_set_int("timestamp", self._TimestampO)

    # services
    def Elementcreated(self, element_id, token):
        if token == TEXT_TOKEN:
            self.text_id = element_id
        # ... others tokens can be used here for different graphical components
