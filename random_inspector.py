from logging.handlers import RotatingFileHandler
import json
import logging
import os
import random
import socket
import protocol

host = "localhost"
port = 12000

"""
set up fantom logging
"""
fantom_logger = logging.getLogger()
fantom_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s :: %(levelname)s :: %(message)s", "%H:%M:%S")
# file
if os.path.exists("./logs/fantom.log"):
    os.remove("./logs/fantom.log")
file_handler = RotatingFileHandler('./logs/fantom.log', 'a', 1000000, 1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
fantom_logger.addHandler(file_handler)
# stream
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
fantom_logger.addHandler(stream_handler)


class Game:
    def __init__(self) -> None:
        self.questions = {"select character": self.select_character,
                          "select position": self.select_position,
                          "activate white power": self.activate_white_power,
                          "activate purple power": self.activate_purple_power,
                          "activate black power": self.activate_black_power,
                          "activate grey power": self.activate_grey_power,
                          "activate brown power": self.activate_brown_power,
                          "grey character power": self.grey_character_power,
                          "purple character power": self.purple_character_power,
                          "brown character power": self.brown_character_power,
                          "blue character power room": self.blue_character_power_room,
                          "blue character power exit": self.blue_character_power_exit,
                          "white character power move": self.white_character_power_move}
        self.char = None

    def update_and_answer(self, data):
        self.data = data
        self.answers = data["data"]
        self.game_state = data["game state"]
        self.chars = data["game state"]["characters"]
        self.phantom = next(
            x for x in self.chars if x["color"] == self.game_state["fantom"])
        self.shadow: int = self.game_state["shadow"]
        self.rooms = []
        self.init_rooms()

        return self.answer()

    def init_rooms(self):
        first, second = self.data["game state"]["blocked"]
        normal_passages = [[1, 4], [0, 2], [1, 3], [2, 7], [0, 5, 8],
                           [4, 6], [5, 7], [3, 6, 9], [4, 9], [7, 8]]

        pink_passages = [[1, 4], [0, 2, 5, 7], [1, 3, 6], [2, 7], [0, 5, 8, 9],
                         [4, 6, 1, 8], [5, 7, 2, 9], [3, 6, 9, 1], [4, 9, 5],
                         [7, 8, 4, 6]]

        # setup blocks
        for idx, paths in enumerate(normal_passages):
            if idx == first and second in paths:
                paths.remove(second)
            if idx == second and first in paths:
                paths.remove(first)

        # setup rooms
        for idx, (normal, pink) in enumerate(zip(normal_passages, pink_passages)):
            chars_in_room = [x for x in self.chars if x["position"] == idx]
            self.rooms.append(dict({
                "idx": idx,
                "chars": chars_in_room,
                "blackout": self.shadow == idx,
                "normal": normal,
                "pink": pink
            }))

    def answer(self):
        if self.data['question type'].startswith("white character power move"):
            self.target = self.data['question type'].split()[-1]
            return self.white_character_power_move()

        return self.questions[self.data["question type"]]()

    def random_answer(self):
        ''' return random answer from question '''

        fantom_logger.debug("--- Random answer ---")
        return random.randint(0, len(self.data["data"])-1)

    # TODO: not working
    def available_paths(self, char):
        chars_in_room = len([
            x for x in self.chars if x["position"] == char["position"]])

        room = next(x for x in self.rooms if x["idx"] == char["position"])

        rooms = []

        def foo(room, n):
            rooms.append(room)
            if n == 0:
                return
            next_rooms = next(x["normal"]
                              for x in self.rooms if x["idx"] == room)
            if room in next_rooms:
                next_rooms.remove(room)
            for next_room in next_rooms:
                foo(next_room, n - 1)

        foo(room["idx"], chars_in_room - 1)
        return rooms

    def select_character(self):
        ''' select characters with most useful powers first '''

        scores = {
            "black": 0,
            "blue": 1,
            "pink": 2,
            "brown": 3,
            "purple": 4,
            "white": 5,
            "red": 6,
            "grey": 7,
        }
        chars_scores = [-1] * len(self.answers)

        for idx, char in enumerate(self.answers):
            chars_scores[idx] = scores[char["color"]]
            chars_in_room = [
                x for x in self.chars if x["position"] == char["position"]]
            if len(chars_in_room) == 1:
                chars_scores[idx] = chars_scores[idx] - 30
            else:
                chars_scores[idx] = chars_scores[idx] + 10
            if char["suspect"] == True:
                chars_scores[idx] = chars_scores[idx] + 30

        idx = chars_scores.index(max(chars_scores))
        self.char = self.answers[idx]
        return idx

    def select_position(self):
        rooms = self.answers

        def move_in_shadow():
            for idx, room in enumerate(rooms):
                if room == self.shadow:
                    return idx
            return None

        def move_in_empty_room():
            for idx, room in enumerate(rooms):
                chars_in_room = [
                    x for x in self.chars if x["position"] == room]
                if len(chars_in_room) == 0:
                    return idx
            return None

        idx = move_in_shadow()
        if idx == None:
            idx = move_in_empty_room()
        return idx if idx != None else self.random_answer()

    # makes people flee in other rooms

    def activate_white_power(self):
        return 0

    def activate_purple_power(self):
        return 0

    # do not use power cause gathering people is bad
    # TODO: maybe use it if in blackout room

    def activate_black_power(self):
        return 0

    def activate_grey_power(self):
        exit()

    def activate_grey_power(self):
        return 1

    def activate_brown_power(self):
        chars = [x for x in self.chars if x["color"] != "brown"]
        brown = next(x for x in self.chars if x["color"] == "brown")
        chars_in_room = [
            x for x in chars if x["position"] == brown["position"]]
        suspects_in_room = [x for x in chars_in_room if x["suspect"] == True]

        # activate power if not enough suspects in room
        return 0 if len(suspects_in_room) > 1 else 1

    def grey_character_power(self):
        rooms = self.answers

        def blackout_phantom_room():
            for idx, room in enumerate(rooms):
                chars_in_room = [
                    x for x in self.chars if x["position"] == room]
                phantom = next(
                    (x for x in chars_in_room if x["color"] == [self.phantom["color"]]), None)
                if phantom:
                    return idx
            return None

        def blackout_room_with_most_suspects():
            best_room = {
                "idx": None,
                "suspects_count": 0
            }
            for idx, room in enumerate(rooms):
                chars_in_room = [
                    x for x in self.chars if x["position"] == room]
                suspects_in_room = [
                    x for x in chars_in_room if x["suspect"] == True]
                if len(suspects_in_room) > best_room["suspects_count"]:
                    best_room["idx"] = idx
                    best_room["suspects_count"] = len(suspects_in_room)

            return best_room["idx"] if best_room["idx"] else None

        idx = blackout_phantom_room()
        if idx == None:
            idx = blackout_room_with_most_suspects()
        return idx if idx != None else self.random_answer()

    def brown_character_power(self):
        ''' takes first suspect in room '''

        colors = self.answers
        chars = [x for x in self.chars if x["color"] != "brown"]
        chars = [x for x in chars if x["color"] in colors]
        suspects = [x for x in chars if x["suspect"] == True]

        return colors.index(suspects[0]["color"]) if len(suspects) > 0 else self.random_answer()

    def purple_character_power(self):
        ''' swap position with innocent alone in room '''

        colors = self.answers
        chars = [x for x in self.chars if x["color"] != "purple"]

        def alone_or_blackout(xs): return [
            x for x in xs if x["position"] == self.shadow or len([y for y in chars if x["position"] == y["position"]]) == 0]

        innocents = [x for x in chars if x["suspect"] == False]
        for innocent in zip(innocents, alone_or_blackout(innocents)):
            if innocent[1] == True:
                return innocent[0]["color"]

        return self.random_answer()

    # TODO

    def blue_character_power_room(self):
        return self.random_answer()

    # TODO

    def blue_character_power_exit(self):
        return self.random_answer()

    def white_character_power_move(self):
        target = self.target
        rooms_id = self.answers
        rooms = []

        for idx, room_id in enumerate(rooms_id):
            # place character in shadow if possible
            if self.shadow == room_id:
                return idx

            chars_in_room = [x for x in self.chars if x["position"] == room_id]
            suspects = len([x for x in chars_in_room if x["suspect"] == True])
            room = {"id": idx,
                    "characters": len(chars_in_room),
                    "suspects": suspects}
            rooms.append(dict(room))

        # sort rooms by chars
        rooms = list(sorted(rooms, key=lambda k: k['characters']))

        # TODO: should not use power if no viable targets
        # place character in room with other suspects if there is any room with suspects else put him in random room
        return rooms[0]["id"] if rooms[0]["suspects"] > 0 else self.random_answer()


class Player():

    def __init__(self):
        self.end = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.game = Game()

    def connect(self):
        self.socket.connect((host, port))

    def reset(self):
        self.socket.close()

    def answer(self, question):

        response_index = self.game.update_and_answer(question)

        return response_index

    def handle_json(self, data):
        data = json.loads(data)
        response = self.answer(data)

        fantom_logger.debug(f"question : %s" % data["question type"])
        fantom_logger.debug(f"answers: %s" % data["data"])
        fantom_logger.debug(f"response: %s" % data["data"][response])
        fantom_logger.debug(f"state: %s\n" % data["game state"])
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


def main():
    p = Player()
    p.run()


main()
