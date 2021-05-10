# -*- coding: utf-8 -*-


from player.parser import *
from r2a.ir2a import IR2A
import time
import math
from base.whiteboard import Whiteboard


class R2AAdaptive(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi_list = []
        self.request_time = 0
        self.real_throughput_list = []
        self.estimated_throughput_list = []
        self.constraint_list = []
        self.mu = 0.2
        self.k = 21
        self.p0 = 0.25
        self.whiteboard = Whiteboard.get_instance()

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi_list = parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        self.real_throughput_list.append(msg.get_bit_length() / t)
        self.real_throughput_list.append(msg.get_bit_length() / t)
        print(self.real_throughput_list[-1])

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        self.calculate_estimated_throughput()
        self.calculate_constraint()
        print("Nosso QI")
        print(self.calculate_quality_id())
        print("Nosso RC")
        print(self.constraint_list[-1])
        msg.add_quality_id(self.calculate_quality_id())
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.real_throughput_list.append(msg.get_bit_length() / t)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    def calculate_delta(self):
        denominador = 1 + math.exp(-self.k * (self.calculate_p() - self.p0))
        return 1 / denominador

    def calculate_estimated_throughput(self):
        if len(self.estimated_throughput_list) <= 2:
            self.estimated_throughput_list.append(self.real_throughput_list[-1])
        else:
            delta = self.calculate_delta()
            te2 = self.estimated_throughput_list[-2]
            ts1 = self.real_throughput_list[-1]
            te = (1 - delta) * te2 + delta * ts1
            self.estimated_throughput_list.append(te)

    def calculate_constraint(self):
        constraint = (1 - self.mu) * self.estimated_throughput_list[-1]
        self.constraint_list.append(constraint)

    def calculate_p(self):
        return (abs(self.real_throughput_list[-1] - self.estimated_throughput_list[-1]) /
                self.estimated_throughput_list[-1])

    def calculate_quality_id(self):
        last_rc = self.constraint_list[-1]

        if len(self.whiteboard.get_playback_buffer_size()) == 0:
            return self.qi_list[0]

        if self.whiteboard.get_playback_buffer_size()[-1][1] >= 20:
            self.mu = 0.10
            self.k = 23
        else:
            self.mu = 0.2
            self.k = 21

        best_qi = self.qi_list[0]
        for qi in self.qi_list:
            if best_qi < qi <= last_rc:
                best_qi = qi
        return best_qi
