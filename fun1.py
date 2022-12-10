import numpy as np
import chess
import chess_pgn
import chess_engine
import chess_svg
from time import sleep
import scipy.io.wavfile

# setup parameters
board_piece=['R','N','B','Q','K']
board_file=chess.FILE_NAMES
board_rank=chess.RANK_NAMES
board_misc=['x','-','O','#','+']
piece_freq=[175,220,131,165,195,247]        # in order: pawn, rook, knight, bishop, queen, king
Fs=44100                                    # sampling frequency
dur=350                                     # note duration in miliseconds

# open game and detect moves
pgn = open('/home/parth/iitb/misc/chess_audio_converter/chess_game1.pgn', encoding='utf-8')
game = chess_pgn.read_game(pgn)
moves = game.mainline_moves()

# parse moves and create frequency pattern
for k1 in moves:
    d = list(k1)
    for k2 in d:
        if(board_piece.count(k2)): p = board_piece.count(k2)+1
        else: p=0
        if(board_rank.count(k2)): r = board_rank.count(k2)-1
        if(board_misc.count(k2)): m = board_misc.count(k2)
    base_freq = piece_freq[p]
    tune_freq = base_freq*2^(r/12)
    x = create_tone(tune_freq,dur,Fs)
    
def create_tone(freq,dur,Fs):
    t = np.linspace(0,dur,int(Fs*dur))
    x = np.cos(2*np.pi*freq*t)
    return x









