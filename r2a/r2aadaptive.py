# -*- coding: utf-8 -*-

# Alunos envolvidos
# Larissa Santana de Freitas Andrade - 18/0021702
# Gabriel Porto Oliveira - 18/0058975

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
        # coletando qi da mensagem
        self.qi_list = parsed_mpd.get_qi()
        # calculando o tempo tomado para transmitir o primeiro pacote
        t = time.perf_counter() - self.request_time
        # salvando a taxa de banda no vetor de bandas reais
        self.real_throughput_list.append(msg.get_bit_length() / t)
        self.real_throughput_list.append(msg.get_bit_length() / t)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        # calculando taxa de vazão estimado
        self.calculate_estimated_throughput()
        # calculando limite da rede
        self.calculate_constraint()
        # adicionando o id calculado na mensagem
        msg.add_quality_id(self.calculate_quality_id())
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        # calculando o tamanho de cada pacote
        t = time.perf_counter() - self.request_time
        # calculando a taxa de transferência e salvando no vetor de taxas reais
        self.real_throughput_list.append(msg.get_bit_length() / t)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    def calculate_delta(self):
        # calculando delta
        denominador = 1 + math.exp(-self.k * (self.calculate_p() - self.p0))
        return 1 / denominador

    def calculate_estimated_throughput(self):
        # checando o tamanho do vetor estimado
        if len(self.estimated_throughput_list) <= 2:
            # caso o tamanho seja menor ou igual a 2 adicionamos o valor real
            self.estimated_throughput_list.append(self.real_throughput_list[-1])
        else:
            delta = self.calculate_delta()
            te2 = self.estimated_throughput_list[-2]
            ts1 = self.real_throughput_list[-1]
            # calculando o valor de throughput estimado
            te = (1 - delta) * te2 + delta * ts1
            self.estimated_throughput_list.append(te)

    def calculate_constraint(self):
        # calculando o limite da rede
        constraint = (1 - self.mu) * self.estimated_throughput_list[-1]
        self.constraint_list.append(constraint)

    def calculate_p(self):
        # calculando a variável p
        return (abs(self.real_throughput_list[-1] - self.estimated_throughput_list[-1]) /
                self.estimated_throughput_list[-1])

    def calculate_quality_id(self):
        last_rc = self.constraint_list[-1]
        # checa se o buffer esta vazio
        if len(self.whiteboard.get_playback_buffer_size()) == 0:
            return self.qi_list[0]

        # caso o tamanho do buffer seja maior ou igual a 20 definimos os valores otimizados
        if self.whiteboard.get_playback_buffer_size()[-1][1] >= 20:
            self.mu = 0.10
            self.k = 23
        else:
            self.mu = 0.2
            self.k = 21
        # definindo o melhor qi
        # sempre pegamos a melhor qualidade possível
        best_qi = self.qi_list[0]
        for qi in self.qi_list:
            if best_qi < qi <= last_rc:
                best_qi = qi
        return best_qi
