"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
import traceback
import random
from sys import stdin, stdout, stderr
from board_util import (
    GoBoardUtil,
    BLACK,
    WHITE,
    EMPTY,
    BORDER,
    PASS,
    MAXSIZE,
    coord_to_point,
)
import numpy as np
import re


class GtpConnection:
    def __init__(self, go_engine, board, debug_mode=False):
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board: 
            Represents the current board state.
        """
        self._debug_mode = debug_mode
        self.go_engine = go_engine
        self.board = board
        self.commands = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_game_id": self.gogui_rules_game_id_cmd,
            "gogui-rules_board_size": self.gogui_rules_board_size_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_side_to_move": self.gogui_rules_side_to_move_cmd,
            "gogui-rules_board": self.gogui_rules_board_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "gogui-analyze_commands": self.gogui_analyze_cmd
        }

        # used for argument checking
        # values: (required number of arguments,
        #          error message on argnum failure)
        self.argmap = {
            "boardsize": (1, "Usage: boardsize INT"),
            "komi": (1, "Usage: komi FLOAT"),
            "known_command": (1, "Usage: known_command CMD_NAME"),
            "genmove": (1, "Usage: genmove {w,b}"),
            "play": (2, "Usage: play {b,w} MOVE"),
            "legal_moves": (1, "Usage: legal_moves {w,b}"),
        }

    def write(self, data):
        stdout.write(data)

    def flush(self):
        stdout.flush()

    def start_connection(self):
        """
        Start a GTP connection. 
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command):
        """
        Parse command string and execute it
        """
        if len(command.strip(" \r\t")) == 0:
            return
        if command[0] == "#":
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()

        elements = command.split()
        if not elements:
            return
        command_name = elements[0]
        args = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".format(traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error("Unknown command")
            stdout.flush()

    def has_arg_error(self, cmd, argnum):
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg):
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg):
        """ Send error msg to stdout """
        stdout.write("? {}\n\n".format(error_msg))
        stdout.flush()

    def respond(self, response=""):
        """ Send response to stdout """
        stdout.write("= {}\n\n".format(response))
        stdout.flush()

    def reset(self, size):
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)

    def board2d(self):
        return str(GoBoardUtil.get_twoD_board(self.board))

    def protocol_version_cmd(self, args):
        """ Return the GTP protocol version being used (always 2) """
        self.respond("2")

    def quit_cmd(self, args):
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args):
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args):
        """ Return the version of the  Go engine """
        self.respond(self.go_engine.version)

    def clear_board_cmd(self, args):
        """ clear the board """
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args):
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

        """
    ==========================================================================
    Assignment 1 - game-specific commands start here
    ==========================================================================
    """

    def gogui_analyze_cmd(self, args):
        """ We already implemented this function for Assignment 1 """
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    def gogui_rules_game_id_cmd(self, args):
        """ We already implemented this function for Assignment 1 """
        self.respond("Gomoku")

    def gogui_rules_board_size_cmd(self, args):
        """ We already implemented this function for Assignment 1 """
        self.respond(str(self.board.size))

    def gogui_rules_legal_moves_cmd(self, args):
        """ Implement this function for Assignment 1 """

        game = self.gogui_rules_final_result_cmd_copy()

        if (game == "black") or (game == "white"):
            self.respond()
        else:
            gtp_moves = [] # Initiable list of legal moves
            for i in range(2): # For both white and black
                color = i+1
                moves = GoBoardUtil.generate_legal_moves(self.board, color) # Get the legal move
                for move in moves:
                    coords = point_to_coord(move, self.board.size) 
                    if format_point(coords).lower() not in gtp_moves: # if the move is not in gtp_moves
                        gtp_moves.append(format_point(coords).lower()) # Then append it
            sorted_moves = " ".join(sorted(gtp_moves)) # Sort them in order
            self.respond(sorted_moves) # Respond with the moves
            return

    def gogui_rules_side_to_move_cmd(self, args):
        """ We already implemented this function for Assignment 1 """
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)

    def gogui_rules_board_cmd(self, args):
        """ We already implemented this function for Assignment 1 """
        size = self.board.size
        str = ''
        for row in range(size-1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                #str += '.'
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)
            
    def gogui_rules_final_result_cmd(self, args):
        """ Implement this function for Assignment 1 """

        # Check for Black
        black_points = self.board.get_black_points() # get all the black points
        black_win = False # black in not winning by default

        for item in black_points: # Black Vertical check
            if (item+(self.board.size+1)*1) in black_points: # Check for 5 in a row vertically down
                if (item+(self.board.size+1)*2) in black_points:
                    if (item+(self.board.size+1)*3) in black_points:
                        if (item+(self.board.size+1)*4) in black_points:
                            black_win = True # If all the satisfies then black wins
        for item in black_points: # Black Horizontal check
            if (item+1) in black_points: # Check for 5 in a row horizontally to the right
                if (item+2) in black_points:
                    if (item+3) in black_points:
                        if (item+4) in black_points:
                            black_win = True # If all the satisfies then black wins
        for item in black_points: # Black Diagonal left check
            if (item+(self.board.size+1)*1-1) in black_points: # Check for 5 in a row from top right to bottom left
                if (item+(self.board.size+1)*2-2) in black_points:
                    if (item+(self.board.size+1)*3-3) in black_points:
                        if (item+(self.board.size+1)*4-4) in black_points:
                            black_win = True # If all the satisfies then black wins
        for item in black_points: # Black Diagonal right check
            if (item+(self.board.size+1)*1+1) in black_points: # Check for 5 in a row from top left to bottom right
                if (item+(self.board.size+1)*2+2) in black_points:
                    if (item+(self.board.size+1)*3+3) in black_points:
                        if (item+(self.board.size+1)*4+4) in black_points:
                            black_win = True # If all the satisfies then black wins
        
        # Check for White
        white_points = self.board.get_white_points() # Get all the white points
        white_win = False # White is not winning by default

        for item in white_points: # White Vertical check
            if (item+(self.board.size+1)*1) in white_points: # Check for 5 in a row vertically down
                if (item+(self.board.size+1)*2) in white_points:
                    if (item+(self.board.size+1)*3) in white_points:
                        if (item+(self.board.size+1)*4) in white_points:
                            white_win = True # If all the satisfies then white wins
        for item in white_points: # White Horizontal check
            if (item+1) in white_points: # Check for 5 in a row horizontally to the right
                if (item+2) in white_points:
                    if (item+3) in white_points:
                        if (item+4) in white_points:
                            white_win = True # If all the satisfies then white wins
        for item in white_points: # White Diagonal left check
            if (item+(self.board.size+1)*1-1) in white_points: # Check for 5 in a row from top right to bottom left
                if (item+(self.board.size+1)*2-2) in white_points:
                    if (item+(self.board.size+1)*3-3) in white_points:
                        if (item+(self.board.size+1)*4-4) in white_points:
                            white_win = True # If all the satisfies then white wins
        for item in white_points: # White Diagonal right check
            if (item+(self.board.size+1)*1+1) in white_points: # Check for 5 in a row from top left to bottom right
                if (item+(self.board.size+1)*2+2) in white_points:
                    if (item+(self.board.size+1)*3+3) in white_points:
                        if (item+(self.board.size+1)*4+4) in white_points:
                            white_win = True # If all the satisfies then white wins

        if black_win == True:
            self.respond("black") # If black wins then respond "black"
        elif white_win == True:
            self.respond("white") # If white wins then respond "white"
        else:
            if (len(self.board.get_empty_points())) == 0:
                self.respond("draw") # If no one wins and board is full, then the result is "draw"
            else:
                self.respond("unknown") # If no one wins and board is NOT full, then the result is "unknown"


    def play_cmd(self, args):
        """ Modify this function for Assignment 1 """
        """
        play a move args[1] for given color args[0] in {'b','w'}
        """
        if args[0] != 'w' and args[0] != 'W' and args[0] != 'b' and args[0] != 'B' and args[0] != 'e' and args[0] != 'E':
                self.respond('illegal move: "{}" wrong color'.format(args[0]))
        else:
            try:
                board_color = args[0].lower()
                board_move = args[1]
                color = color_to_int(board_color)
                
                coord = move_to_coord(args[1], self.board.size)
                if coord:
                    move = coord_to_point(coord[0], coord[1], self.board.size)
                else:
                    self.error(
                        "Error executing move {} converted from {}".format(move, args[1])
                    )
                    return
                if not self.board.play_move(move, color):
                    self.respond('illegal move: "{}" occupied'.format(board_move))
                    return
                else:
                    self.debug_msg(
                        "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                    )
                self.respond()
            except Exception as e:
                self.respond('illegal move: {}'.format(str(e)))

    def genmove_cmd(self, args):
        """ Modify this function for Assignment 1 """
        """ generate a move for color args[0] in {'b','w'} """
        game = self.gogui_rules_final_result_cmd_copy()
        if (game == "black") or (game == "white"):
            self.respond("resign")
        else:
            try:

                board_color = args[0].lower()
                color = color_to_int(board_color)

                gtp_moves = []
                for i in range(2):
                    colour = i+1
                    moves = GoBoardUtil.generate_legal_moves(self.board, colour)

                move = moves[random.randint(0,len(moves)-1)]

                coords = point_to_coord(move, self.board.size)
                if format_point(coords).lower() not in gtp_moves:
                    gtp_moves.append(format_point(coords).lower())

                self.board.play_move(move, color)
                self.respond(gtp_moves[0])

            except:
                game = self.gogui_rules_final_result_cmd_copy()
                if game == "draw":
                    self.respond("pass")
                elif (game == "black") or (game == "white"):
                    self.respond("resign")


    # IGNORE THIS FUNCTION - COPY of  gogui_rules_final_result_cmd
    def gogui_rules_final_result_cmd_copy(self):
        """ Implement this function for Assignment 1 """

        # Check for Black
        black_points = self.board.get_black_points()
        black_win = False

        for item in black_points: # Black Vertical check
            if (item+(self.board.size+1)*1) in black_points:
                if (item+(self.board.size+1)*2) in black_points:
                    if (item+(self.board.size+1)*3) in black_points:
                        if (item+(self.board.size+1)*4) in black_points:
                            black_win = True
        for item in black_points: # Black Horizontal check
            if (item+1) in black_points:
                if (item+2) in black_points:
                    if (item+3) in black_points:
                        if (item+4) in black_points:
                            black_win = True
        for item in black_points: # Black Diagonal left check
            if (item+(self.board.size+1)*1-1) in black_points:
                if (item+(self.board.size+1)*2-2) in black_points:
                    if (item+(self.board.size+1)*3-3) in black_points:
                        if (item+(self.board.size+1)*4-4) in black_points:
                            black_win = True
        for item in black_points: # Black Diagonal right check
            if (item+(self.board.size+1)*1+1) in black_points:
                if (item+(self.board.size+1)*2+2) in black_points:
                    if (item+(self.board.size+1)*3+3) in black_points:
                        if (item+(self.board.size+1)*4+4) in black_points:
                            black_win = True

        
        # Check for White
        white_points = self.board.get_white_points()
        white_win = False

        for item in white_points: # White Vertical check
            if (item+(self.board.size+1)*1) in white_points:
                if (item+(self.board.size+1)*2) in white_points:
                    if (item+(self.board.size+1)*3) in white_points:
                        if (item+(self.board.size+1)*4) in white_points:
                            white_win = True
        for item in white_points: # White Horizontal check
            if (item+1) in white_points:
                if (item+2) in white_points:
                    if (item+3) in white_points:
                        if (item+4) in white_points:
                            white_win = True
        for item in white_points: # White Diagonal left check
            if (item+(self.board.size+1)*1-1) in white_points:
                if (item+(self.board.size+1)*2-2) in white_points:
                    if (item+(self.board.size+1)*3-3) in white_points:
                        if (item+(self.board.size+1)*4-4) in white_points:
                            white_win = True
        for item in white_points: # White Diagonal right check
            if (item+(self.board.size+1)*1+1) in white_points:
                if (item+(self.board.size+1)*2+2) in white_points:
                    if (item+(self.board.size+1)*3+3) in white_points:
                        if (item+(self.board.size+1)*4+4) in white_points:
                            white_win = True

        if black_win == True:
            return("black")
        elif white_win == True:
            return("white")
        else:
            if (len(self.board.get_empty_points())) == 0:
                return("draw")
            else:
                return("unknown")


    """
    ==========================================================================
    Assignment 1 - game-specific commands end here
    ==========================================================================
    """

    def showboard_cmd(self, args):
        self.respond("\n" + self.board2d())

    def komi_cmd(self, args):
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args):
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args):
        """ list all supported GTP commands """
        self.respond(" ".join(list(self.commands.keys())))

    """ Assignment 1: ignore this command, implement 
        gogui_rules_legal_moves_cmd  above instead """
    def legal_moves_cmd(self, args):
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        moves = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))
        self.respond(sorted_moves)


def point_to_coord(point, boardsize):
    """
    Transform point given as board array index 
    to (row, col) coordinate representation.
    Special case: PASS is not transformed
    """
    if point == PASS:
        return PASS
    else:
        NS = boardsize + 1
        return divmod(point, NS)


def format_point(move):
    """
    Return move coordinates as a string such as 'A1', or 'PASS'.
    """
    assert MAXSIZE <= 25
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    if move == PASS:
        return "PASS"
    row, col = move
    if not 0 <= row < MAXSIZE or not 0 <= col < MAXSIZE:
        raise ValueError
    return column_letters[col - 1] + str(row)


def move_to_coord(point_str, board_size):
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    Raises ValueError if point_str is invalid
    """
    if not 2 <= board_size <= MAXSIZE:
        raise ValueError("board_size out of range")
    s = point_str.lower()
    if s == "pass":
        return PASS
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        col = ord(col_c) - ord("a")
        if col_c < "i":
            col += 1
        row = int(s[1:])
        if row < 1:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError('"{}"'.format(s))
    if not (col <= board_size and row <= board_size):
        raise ValueError('"{}" wrong coordinate'.format(s))
    return row, col


def color_to_int(c):
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK, "w": WHITE, "e": EMPTY, "BORDER": BORDER}
    return color_to_int[c]
