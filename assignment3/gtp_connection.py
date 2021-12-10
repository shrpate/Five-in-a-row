"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
from abc import abstractproperty
import traceback
from sys import stdin, stdout, stderr

from numpy.core.fromnumeric import _cumprod_dispatcher
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
        self.policy = "rule_based"
        self.N = 10
        self.moves = []
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
            "gogui-analyze_commands": self.gogui_analyze_cmd,

            # Assignment 3 commands
            "policy": self.policy_cmd,
            "policy_moves": self.policy_moves_cmd
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
        
    def play_cmd(self, args):
        """
        play a move args[1] for given color args[0] in {'b','w'}
        """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            color = color_to_int(board_color)
            if args[1].lower() == "pass":
                self.board.play_move(PASS, color)
                self.board.current_player = GoBoardUtil.opponent(color)
                self.respond()
                return
            coord = move_to_coord(args[1], self.board.size)
            if coord:
                move = coord_to_point(coord[0], coord[1], self.board.size)
            else:
                self.respond("unknown: {}".format(args[1]))
                return
            if not self.board.play_move(move, color):
                self.respond("illegal move: \"{}\" occupied".format(args[1].lower()))
                return
            else:
                self.debug_msg(
                    "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                )
            self.respond()
        except Exception as e:
            self.respond("illegal move: {}".format(str(e).replace('\'','')))
    
    # --------------------------------------------------------------------------------------------------------------
    def policy_cmd(self, args):
        if args[0] == "random" or args[0] == "rule_based":
            self.policy = args[0] # Set the policy
            self.respond()
        else:
            # If it is incorrect policy, throw an error.
            string = "ERROR: " + args[0] + " is not a valid policy. Choose 'rule_based' or 'random'"
            self.respond(string)
    
    def random(self):
        current_player = self.board.current_player # Current player
        empty = self.board.get_empty_points() # Get empty points
        np.random.shuffle(empty) # Shuffle it for simulation
        player = current_player # re-define the current player
        final_moves = [] # Final move list 
        for j in range(self.N): # Run it 10 times
            moves = [] # Temp moves
            for i in range(len(empty)): # loop
                if len(moves) == 0: # If it is empty
                    moves.append(empty[i]) # Only then append
                self.board.play_move(empty[i], player) # play the move
                result = self.board.detect_five_in_a_row() # Detect five in a row
                if result == current_player or result == 0: # If the current player is a winner or if it ends in a draw
                    final_moves.append(moves[0]) # append the current move to final_moves list
                player = GoBoardUtil.opponent(player) # Change the current player to opponent player
                
            # UNDO THE MOVES
            for i in range(len(empty)):
                self.board.set_color(0, empty[i])
        
        final_moves = list(set(final_moves)) # Remove all the duliplcates

        return final_moves # Return
    
    # WIN FUNCTION MODIFIED
    def win_modified(self, player):
        empty = self.board.get_empty_points() # Get empty points
        current_player = player # Current player
        for i in range(len(empty)): # Loop
            self.board.play_move(empty[i], player) # Play the move
            result = self.board.detect_five_in_a_row() # Detect five in a row
            self.board.set_color(0, empty[i]) # Undo the move
            if result == current_player:
                return empty[i] # Return the move
    
    # WIN FUNCTION
    def win(self, player):
        empty = self.board.get_empty_points() # Get empty points
        for i in range(len(empty)): # Loop
            self.board.play_move(empty[i], player) # Play the move
            result = self.board.detect_five_in_a_row() # Detect five in a row
            if result == player: # If the current player if the winner
                self.moves.append(empty[i]) # append the moves to the list
            self.board.set_color(0, empty[i]) # UNDO the Move
        
    # OPEN FOUR FUNCTION
    def openFour(self, player):
        empty_o = self.board.get_empty_points() # Get empty points
        for i in range(len(empty_o)): # loop
            self.board.play_move(empty_o[i], player) # Play the move
            move = self.win_modified(player) # Run the win function
            if move != None: # if move is not empty
                self.board.play_move(move, GoBoardUtil.opponent(player)) # Play the move
                empty = self.board.get_empty_points() # Get new empty points
                for j in range(len(empty)): # loop
                    self.board.play_move(empty[j], player) # Play the move
                    result = self.board.detect_five_in_a_row() # Detect five in a row
                    self.board.set_color(0, empty[j]) # Undo the last move
                    self.board.set_color(0, move) # Undo second last move/ second move
                    self.board.set_color(0, empty_o[i]) # Undo the first move
                    if result == player: # If current player is the winner, 
                        self.moves.append(empty_o[i]) # Append the move
            
        # UNDO all the moves made
        for i in range(len(empty_o)):
            self.board.set_color(0, empty_o[i])

    # BLOCK OPEN FOUR FUNCTION
    def blockOpenFour(self, player):
        empty_o = self.board.get_empty_points() # Get empty points
        for i in range(len(empty_o)): # Loop
            self.board.play_move(empty_o[i], player) # Play the move
            result4 = self.board.detect_four_in_a_row() # Detect 4 in a row
            if result4 == player: # If the current player has 4 in a row than move further with this function
                empty = self.board.get_empty_points() # Get new empty points
                for j in range(len(empty)): # loop
                    self.board.play_move(empty[j], player) # Play the move
                    result5 = self.board.detect_five_in_a_row() # now detect 5 in a row
                    if result5 == player and empty_o[i] not in self.moves: # if the move is a winner move for the current player,
                        self.moves.append(empty_o[i]) # then append the original move made to the list
                    self.board.set_color(0, empty[j]) # UNDO the last move
            self.board.set_color(0, empty_o[i]) # Undo the first move

    def rule_based(self):
        current_player = self.board.current_player # Current player
        opponent_player = GoBoardUtil.opponent(current_player) # Opponent
        
        # DirectWin
        action = "Win" # Define the action
        func = self.win(current_player) # Run the win function on the current player
        if len(self.moves) != 0: # If move(s) is(are) found, then terminate the function
            return action, self.moves # return the action and moves
        else:   # else move on
            # BlockWin
            action = "BlockWin" # Define new action
            func = self.win(opponent_player) # Run the win function on the opponent player
            if len(self.moves) != 0: # If move(s) is(are) found, then terminate the function
                return action, self.moves # return the action and moves
            else:   # else move on
                # OpenFour
                action = "OpenFour" # Define new action
                func = self.openFour(current_player) # Run the Open Four function on current player
                if len(self.moves) != 0: # If move(s) is(are) found, then terminate the function
                    return action, self.moves # return the action and moves
                else:   # else move on
                    # BlockOpenFour
                    action = "BlockOpenFour" # Define new action
                    func = self.blockOpenFour(opponent_player) # Run the Open Four function on opponent player
                    if len(self.moves) != 0: # If move(s) is(are) found, then terminate the function
                        return action, self.moves # return the action and moves
                    else:
                        # Random if nothing from the above matches
                        action = "Random" # Define last (remaining) action
                        moves = self.random() # Get move(s)
                        return action, moves # return the action and moves

    def policy_moves_cmd(self, args):
        self.moves = [] # Get moves
        empty = self.board.get_empty_points() # Get empty points
        if len(empty) == 0: # if it is empty
            self.respond() # Just respond
            return # and return
        
        if len(empty) == ((self.board.size)*(self.board.size)): # If the board is full
            action = "Random" # define the action
            string = "" # Start and empty string
            moves = self.board.get_empty_points() # Get empty points
            moves_as_string = [] # Get moves list
            for i in moves: # loop
                move_coord = point_to_coord(i, self.board.size) # Convert the moves
                moves_as_string.append(format_point(move_coord)) # Format it
            moves_as_string = sorted(moves_as_string) # Sort it
            
            for i in sorted(moves_as_string):
                string += str(i) + " "
            total = action + " " + string
            self.respond(total)
            return                  # Return it 

        if self.policy == "rule_based": # If the policy is rule based
            string = "" # Get the empty string
            action, moves = self.rule_based() # Get the right action with right moves
            moves_as_string = [] 
            for i in moves: # Loop
                move_coord = point_to_coord(i, self.board.size) # Move to coord
                moves_as_string.append(format_point(move_coord)) # Formate the point

            # Format the string
            for i in moves_as_string:
                string += str(i) + " "
            string_final = action + " " + string
            self.respond(string_final)
            return

        if self.policy == "random": # If the policy is random
            string = "" # Get the empty string
            moves = self.random() # Get the right action with right moves
            moves_as_string = []
            for i in moves: # Loop
                move_coord = point_to_coord(i, self.board.size) # Move to coord
                moves_as_string.append(format_point(move_coord)) # Formate the point

            # Format the string
            for i in moves_as_string:
                string += str(i)
            string_final = "Random " + string
            self.respond(string_final)
            return

    # -------------------------------------------------------------------------------------------------------------
    
    def genmove_cmd(self, args):
        """
        Generate a move for the color args[0] in {'b', 'w'}, for the game of gomoku.
        """
        result = self.board.detect_five_in_a_row()
        if result == GoBoardUtil.opponent(self.board.current_player):
            self.respond("resign")
            return
        if result == self.board.current_player:
            self.respond("pass")
            return
        if self.board.get_empty_points().size == 0:
            self.respond("pass")
            return
        
        board_color = args[0].lower()
        color = color_to_int(board_color)
        self.board.current_player = color
        if self.policy == "rule_based":
            action, moves = self.rule_based()
            move = moves[0]
        if self.policy == "random":
            moves = self.random()
            move = moves[0]

        move_coord = point_to_coord(move, self.board.size)
        move_as_string = format_point(move_coord)
        if self.board.is_legal(move, color):
            self.board.play_move(move, color)
            self.respond(move_as_string.lower())
        else:
            self.respond("Illegal move: {}".format(move_as_string))

    def gogui_rules_game_id_cmd(self, args):
        self.respond("Gomoku")

    def gogui_rules_board_size_cmd(self, args):
        self.respond(str(self.board.size))

    def gogui_rules_legal_moves_cmd(self, args):
        if self.board.detect_five_in_a_row() != EMPTY:
            self.respond("")
            return
        empty = self.board.get_empty_points()
        output = []
        for move in empty:
            move_coord = point_to_coord(move, self.board.size)
            output.append(format_point(move_coord))
        output.sort()
        output_str = ""
        for i in output:
            output_str = output_str + i + " "
        self.respond(output_str.lower())
        return

    def gogui_rules_side_to_move_cmd(self, args):
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)

    def gogui_rules_board_cmd(self, args):
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
        if self.board.get_empty_points().size == 0:
            self.respond("draw")
            return
        result = self.board.detect_five_in_a_row()
        if result == BLACK:
            self.respond("black")
        elif result == WHITE:
            self.respond("white")
        else:
            self.respond("unknown")

    def gogui_analyze_cmd(self, args):
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

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
        raise ValueError("invalid point: '{}'".format(s))
    if not (col <= board_size and row <= board_size):
        raise ValueError("\"{}\" wrong coordinate".format(s))
    return row, col


def color_to_int(c):
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK, "w": WHITE, "e": EMPTY, "BORDER": BORDER}
    
    try:
        return color_to_int[c]
    except:
        raise KeyError("\"{}\" wrong color".format(c))
