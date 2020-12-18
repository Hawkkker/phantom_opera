import json
import logging
import os
import random
import socket
from logging.handlers import RotatingFileHandler

import protocol

host = "localhost"
port = 12000
# HEADERSIZE = 10

"""
set up inspector logging
"""
inspector_logger = logging.getLogger()
inspector_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s :: %(levelname)s :: %(message)s", "%H:%M:%S")
# file
if os.path.exists("./logs/inspector.log"):
    os.remove("./logs/inspector.log")
file_handler = RotatingFileHandler('./logs/inspector.log', 'a', 1000000, 1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
inspector_logger.addHandler(file_handler)
# stream
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
inspector_logger.addHandler(stream_handler)

destination = -1

class Player():

    def __init__(self):

        self.end = False
        # self.old_question = ""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    passages = [{1, 4}, {0, 2}, {1, 3}, {2, 7}, {0, 5, 8}, {4, 6}, {5, 7}, {3, 6, 9}, {4, 9}, {7, 8}]
    pink_passages = [{1, 4}, {0, 2, 5, 7}, {1, 3, 6}, {2, 7}, {0, 5, 8, 9}, {4, 6, 1, 8}, {5, 7, 2, 9}, {3, 6, 9, 1}, {4, 9, 5}, {7, 8, 4, 6}]
    char = list()
    data = list()
    blocked = list()
    shadow = int()
    sus_grouped = list()
    sus_alone = list()
    group = 1
    separate = 2
    default = 0
    yes = 1
    no = 2
    with_suspect = default
    behaviour = group

    # Determine se comportement: si l'on groupe ou sépare les gens
    # Si les suspect sont inférieur ou égale a 5 on sépare
    def determine_behaviour(self):
        sus = 0
        for char in self.char:
            if char['suspect'] == True:
                sus += 1
        if sus <= 5:
            self.behaviour = self.separate
        print("suspect : " + str(sus))
        self.check_groups(True, True)

    # Set le comportement pour le personnage 'char'
    def set_behaviour(self, char):
        ### TODO VERIFIER LES CHANGEMENT DE GROUP/ALONE SI DEPLACEMENT
        if char['suspect'] == True:
            if len(self.nb_in_room(char['position'], False)) == 1:
                if len(self.sus_alone)-1 >= len(self.sus_grouped):
                    # Grouper avec non suspect
                    self.with_suspect = self.no
                    self.behaviour = self.group
                else:
                    self.behaviour = self.separate
            else:
                if len(self.sus_grouped)-1 >= len(self.sus_alone):
                    #  grouper avec un non suspect si un suspect est aussi présent et personne d'autre
                    if self.sus_in_room(self.nb_in_room(char['position'], False), False) > 1 and len(self.nb_in_room(char['position'], False)) == 2:
                        self.with_suspect = self.no
                        self.behaviour = self.group
                    else:
                        self.behaviour = self.separate
                else:
                    self.behaviour = self.group
        else:
            if self.sus_in_room(self.nb_in_room(char['position'], False), False) > 0:
                if len(self.sus_grouped)-1 >= len(self.sus_alone):
                    self.behaviour = self.separate
                else:
                    # grouper avec suspect
                    self.with_suspect = self.yes
                    self.behaviour = self.group
            else:
                if len(self.sus_alone)-1 >= len(self.sus_grouped):
                    # grouper avec suspect
                    self.with_suspect = self.yes
                    self.behaviour = self.group
                else:
                    self.behaviour = self.separate
        print("Behaviour set to : " + str(self.behaviour) + " for char : " + str(char['color']))

    # Retourne les suspect dans 'data' si form est False, sinon en retourne son nombre
    def nb_sus(self, data, form):
        sus = [q for q in data if q['suspect'] == True]
        if form:
            return len(sus)
        else:
            return sus
    
    # Retourne les suspect dans 'data' si form est False, sinon en retourne son nombre
    def nb_clean(self, data, form):
        clean = [q for q in data if q['suspect'] == False]
        if form:
            return len(clean)
        else:
            return clean

    # Retourne la liste des occupants de chaque pièce, 
    # si 'suspect' est true renvoie uniquement les suspects
    def check_rooms(self, suspect):
        pos = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for char in self.char:
            if suspect:
                if char['suspect']:
                    pos[int(char['position'])] += 1
            else:
                pos[int(char['position'])] += 1
        return pos

    # Check et retourne le nombre de personne seule, 
    # Si 'change' est true, modifie le comportement
    def check_groups(self, suspect, change):
        nb_solo = 0
        pos = self.check_rooms(suspect)
        for i, char in enumerate(pos):
            if char == 1 or i == self.shadow:
                nb_solo += 1
        if change:
            self.behaviour = self.group if nb_solo > 3 else self.separate
        return nb_solo

    # Retourne les pièces adjacentes a 'position'
    def get_adjacent_positions_from_position(self, position, charact):
        if charact['color'] == "pink":
            active_passages = self.pink_passages
        else:
            active_passages = self.passages
        return [room for room in active_passages[position] if set([room, position]) != set(self.blocked)]
    
    # Retourne les personnes présentes dans une pièce,
    # Si 'check_playable' est true, on enlève les personnages jouables
    def nb_in_room(self, position, check_playable):
        characters_in_room = [q for q in self.char if q['position'] == position]
        if check_playable:
            tmp = []
            for char in characters_in_room:
                found = False
                for card in self.data:
                    if card == char:
                        found = True
                if not found:
                    tmp.append(char)
            characters_in_room = tmp
        return characters_in_room

    # Retourne le nombre de suspects de 'characters_in_room',
    # Si 'check_playable' est true, on enlève les suspects jouables
    def sus_in_room(self, characters_in_room, check_playable):
        sus = 0
        for char in characters_in_room:                
            if char['suspect'] == True:
                # and not playable
                if check_playable:
                    for playable in self.data:
                        if char == playable:
                            sus -= 1
                sus += 1
        # if not check_playable:
        #     print("char in room = " + str(characters_in_room) + " and suspect nb is : " + str(sus))
        return sus

    # Rempli les tableaux du nombre de suspects seuls ou en groupe
    def fill_sus_tabs(self):
        for char in self.char:
            if char['suspect'] == True:
                if len(self.nb_in_room(char['position'], False)) > 1:
                    self.sus_grouped.append(char)
                else:
                    self.sus_alone.append(char)
        print("suspect grouped : ")
        print(self.sus_grouped)
        print("suspect alone : ")
        print(self.sus_alone)

    # Renvoie le nombre de suspect seul ou en groupe en fonction du comportement
    # si le personnage 'char' se déplace dans la pièce 'position'
    def determine_sus(self, char, position):
        sus_grouped = 0
        sus_alone = 0
        tmp = 0
        i = 0
        while i < len(self.char)-1:
            if self.char[i] == char:
                tmp = self.char[i]['position']
                self.char[i]['position'] = position
                break
            i += 1
        for sus in self.char:
            if sus['suspect'] == True:
                if len(self.nb_in_room(sus['position'], False)) > 1:
                    sus_grouped += 1
                else:
                    sus_alone += 1
        self.char[i]['position'] = tmp
        if self.behaviour == self.group:
            return sus_grouped
        else:
            return sus_alone

    def connect(self):
        self.socket.connect((host, port))

    def reset(self):
        self.socket.close()
    
    # Retourne la liste des positions atteignables par 'char'
    def inrange(self, char):
        chars = self.nb_in_room(char['position'], False)
        nb_char = len(chars)
        available_rooms = list()
        available_rooms.append(self.get_adjacent_positions_from_position(char['position'], char))
        for step in range(1, nb_char):
            next_rooms = list()
            for room in available_rooms[step-1]:
                next_rooms += self.get_adjacent_positions_from_position(room, char)
            available_rooms.append(next_rooms)
        temp = list()
        for sublist in available_rooms:
            for room in sublist:
                temp.append(room)
        temp = set(temp)
        available_positions = list(temp)
        return available_positions

    # Retourne la meilleure pièce ou se déplacer des 'available_positions',
    # Si l'on cherche a grouper, on va renvoyer la pièce contenant le + de suspect
    # Si l'on cherche a séparer, on va renvoyer la pièce contenant le - de suspect
    def worth_going(self, available_positions, check_playable):
        others = []
        best_room = -1
        if self.behaviour == self.group:
            worth = 0
            for room in available_positions:
                # Si l'on doit grouper avec un suspect
                if self.with_suspect == self.yes:
                    sus_there = self.nb_sus(self.char, False)
                    for sus in sus_there:
                        if sus['position'] == room:
                            return room
                    continue
                # Si l'on doit grouper avec un non suspect
                if self.with_suspect == self.no:
                    clean_there = self.nb_clean(self.char, False)
                    for clean in clean_there:
                        if clean['position'] == room:
                            return room
                    continue
                tmp = len(self.nb_in_room(room, check_playable)) 
                if tmp > worth:
                    worth = tmp
                    best_room = room
                elif tmp == worth:
                    others.append(room)
            if check_playable:
                ### TODO REGARDER LA RANGE DES JOUEURS JOUABLES
                if len(self.nb_in_room(best_room, check_playable)) < 1:
                    for room in others:
                        if len(self.nb_in_room(room, check_playable)) < 1:
                            pass
                        else:
                            return room
                    return 10
        elif self.behaviour == self.separate:
            worth = 10
            for room in available_positions:
                tmp = len(self.nb_in_room(room, check_playable))
                if tmp < worth:
                    worth = tmp
                    best_room = room
                elif tmp == worth:
                    others.append(room)
            if check_playable:
                if len(self.nb_in_room(best_room, False)) > 0:
                    for room in others:
                        if len(self.nb_in_room(room, False)) > 0:
                            pass
                        else:
                            return room
                    return 10
        print("worth room for behaviour " + str(self.behaviour) + " and " + str(self.with_suspect) + " is " + str(best_room))
        return best_room

    def select(self):
        if len(self.data) > 1:
            max_sus = 0 if self.behaviour == self.group else 10
            index = 0
            nb_sus = self.nb_sus(self.char, True)
            self.fill_sus_tabs()
            add_alone = 0
            add_group = 0
            global destination
            tmp = 0
            best_dest = -1
            if nb_sus <= 5:
                if nb_sus > 0:
                    sus_playable = self.nb_sus(self.data, False)
                    all_sus = self.nb_sus(self.char, False)
                    for i, char in enumerate(sus_playable):
                        self.set_behaviour(char)
                        rooms = self.inrange(char)
                        tmp = self.worth_going(rooms, True)
                        if tmp != 10:
                            destination = tmp
                            for index, cards in enumerate(self.data):
                                if cards == char:
                                    return index
                    for i, char in enumerate(self.data):
                        self.set_behaviour(char)
                        max_sus = 0 if self.behaviour == self.group else 10
                        rooms = self.inrange(char)
                        tmp = self.worth_going(rooms, True)
                        if tmp != 10:
                            if self.behaviour == self.separate:
                                sus_alone = self.determine_sus(char, tmp)
                                if sus_alone < max_sus:
                                    index = i
                                    max_sus = sus_alone
                                    best_dest = tmp
                            else:
                                sus_grouped = self.determine_sus(char, tmp)
                                if sus_grouped > max_sus:
                                    index = i
                                    max_sus = sus_grouped
                                    best_dest = tmp
                    if best_dest >= 0:
                        destination = best_dest
                        return index
                    # TODO les pouvoirs
                    print("NOTHING WORTH WAS FOUND")
                    return 0
            for i, char in enumerate(self.data):
                rooms = self.inrange(char)
                tmp = self.worth_going(rooms, False)
                if self.behaviour == self.separate:
                    sus_alone = self.determine_sus(char, tmp)
                    if sus_alone < max_sus:
                        index = i
                        max_sus = sus_alone
                        best_dest = tmp
                else:
                    sus_grouped = self.determine_sus(char, tmp)
                    if sus_grouped > max_sus:
                        index = i
                        max_sus = sus_grouped
                        best_dest = tmp
                    elif sus_grouped == max_sus:
                        if char['suspect'] == True:
                            index = i
                            max_sus = sus_grouped
                            best_dest = tmp
            if best_dest >= 0:
                destination = best_dest
                return index
            print("NOTHING WORTH IT WAS FOUND")
            return 0
        else:
            char = self.data[0]
            rooms = self.inrange(char)
            tmp = self.worth_going(rooms, False)
            destination = tmp
            return 0

    def power(self, color):
        return 0

    def position(self):
        pos = self.worth_going(self.data, False)
        index = 0
        global destination
        if destination >= 0:
            pos = destination
            destination = -1
        # Deprecated
        for i, val in enumerate(self.data):
            if val == pos:
                index = i
        return index

    def answer(self, question):
        # work
        print("---------------")
        answer =  question["question type"].split()
        self.data = question["data"]
        self.game_state = question["game state"]
        self.shadow = self.game_state["shadow"]
        self.blocked = self.game_state["blocked"]
        self.char = self.game_state["characters"]
        self.determine_behaviour()
        print("Behaviour : " + str(self.behaviour))
        if len(answer) > 2:
            color = answer[1]
            answer[1] = answer[2]
        if answer[1] == "character":
            response_index = self.select()
        elif answer[1] == "power":
            response_index = self.power(color)
        elif answer[1] == "position":
            response_index = self.position()
        self.sus_grouped = []
        self.sus_alone = []
        self.with_suspect = self.default
        self.behaviour = self.group
        print(answer)
        print(self.data)
        print(self.data[response_index])
        print("----------------")
        inspector_logger.debug("|\n|")
        inspector_logger.debug("inspector answers")
        inspector_logger.debug(f"question type ----- {question['question type']}")
        inspector_logger.debug(f"data -------------- {self.data}")
        inspector_logger.debug(f"response index ---- {response_index}")
        inspector_logger.debug(f"response ---------- {self.data[response_index]}")
        return response_index

    def handle_json(self, data):
        data = json.loads(data)
        response = self.answer(data)
        # send back to server
        bytes_data = json.dumps(response).encode("utf-8")
        protocol.send_json(self.socket, bytes_data)

    def run(self):

        self.connect()

        while self.end is not True:
            received_message = protocol.receive_json(self.socket)
            if received_message:
                self.handle_json(received_message)
            else:
                print("no message, finished learning")
                self.end = True


p = Player()

p.run()
