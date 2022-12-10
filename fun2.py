from parsita import *
from parsita.util import constant
import numpy as np
from scipy.io import wavfile

#import json

def formatannotations(annotations):
    return {ant[0]: ant[1] for ant in annotations}

def formatgame(game):
    return {'moves': game[0],'outcome': game[1]}

def formatentry(entry):
    return {'annotations': entry[0], 'game': entry[1]}

def handleoptional(optionalmove):
    if len(optionalmove) > 0:
        return optionalmove[0]
    else:
        return None

def create_tone(freq,dur,Fs,A):
# generate appropriate major chord with base frequency
    samples = int(Fs/freq)
    cycles = int(freq*dur/1000)
    triagTable = A*np.hstack((np.linspace(1,-1,int(samples/2)),np.linspace(-1,1,int(samples/2))))
    t = np.linspace(0,dur*0.001,len(triagTable)*cycles)
    x = np.tile(triagTable,cycles)
    return x

quote = lit(r'"')
tag = reg(r'[\u0021-\u0021\u0023-\u005A\u005E-\u007E]+')
string = reg(r'[\u0020-\u0021\u0023-\u005A\u005E-\U0010FFFF]+')

whitespace = lit(' ') | lit('\n')

annotation = '[' >> (tag) << ' ' & (quote >> string << quote) << ']'
annotations = repsep(annotation, '\n') > formatannotations

nullmove = lit('--') # Illegal move rarely used in annotations
longcastle = reg(r'O-O-O[+#]?')
castle = reg(r'O-O[+#]?')
regularmove = reg(r'[a-h1-8NBRQKx\+#=]+') # Matches more than just chess moves
move = regularmove | longcastle | castle | nullmove
movenumber = (reg(r'[0-9]+') << '.' << whitespace) > int
turn = movenumber & (move << whitespace) & (opt(move << whitespace) > handleoptional)

draw = lit('1/2-1/2')
white = lit('1-0')
black = lit('0-1')

outcome = draw | white | black
game = (rep(turn) & outcome) > formatgame
entry = ((annotations << rep(whitespace)) & (game << rep(whitespace))) > formatentry
file = rep(entry)# Parse the file

def ParseChessGame(fname):
    with open(fname, 'r') as f:
        parsedoutput = file.parse(f.read()).or_die()
        
    # iterate over moves
    GameMoves = parsedoutput[0]['game']['moves']
    GameLength = len(GameMoves)

    board_piece=['R','N','B','Q','K']
    board_file=['a','b','c','d','e','f','g','h']
    board_rank=[1,2,3,4,5,6,7,8]
    board_misc=['x','-','O','#','+']

    # note assignment in order: pawn, rook, knight, bishop, queen, king
    # 1) pawn-F, rook-A, knight-C, bishop-E, queen-G, king-B 174,220,131,165,196,247
    # 2) pawn-G#, rook-A#, knight-C, bishop-D#, queen-F, king-C# 208,233,262,311,349,277
    # 3) pawn-C, rook-C#, knight-D, bishop-D#, queen-E, king-F 262,277,294,311,330,349
    # 4) random assignment A2*(2**((np.random.choice(36,6,replace=False)-1)/12))
    A2=110          # anchor note
    piece_freq_black=np.array([208,233,262,311,349,277])
    piece_freq_white=piece_freq_black
    
    #print(piece_freq_white)
    Fs=44100                                    # sampling frequency
    dur=450                                     # note duration in miliseconds

    tune = []
    tune_white=[]
    tune_black=[]
    for k1 in GameMoves:
        WhiteMove = k1[1]
        BlackMove = k1[2]
        
        if WhiteMove[0] in board_piece:         # piece move like Nf6, Ndf6, Nxf6, or Ndxf6
            base_freq = piece_freq_white[board_piece.index(WhiteMove[0])+1]
            if WhiteMove[2] in board_misc:      # capture like Ndxf6
                rank = int(WhiteMove[4])+12     # if captures than double the freq
            elif WhiteMove[2] in board_file:    # piece move like Ndf6 or capture like Nxf6
                rank = int(WhiteMove[3])
                if WhiteMove[1] in board_misc:  # if captures than double the freq
                    rank = rank+12
            else:                               # piece move like Nf6
                rank = int(WhiteMove[2])
        
        else:
            if WhiteMove[0] in board_misc:      # castle O-O or O-O-O
                base_freq = piece_freq_white[5]       # if castled, the king move is considered and not rook
                rank = 1                        # for white, castling happens in 1st rank
            else:                               # pawn move like e4 or exd6
                base_freq = piece_freq_white[0]
                if WhiteMove[1] in board_misc:  # pawn capture like exd6 (capture -> double the freq)
                    rank = int(WhiteMove[3])+12
                else:                           # normal pawn move like e4
                    rank = int(WhiteMove[1])

        if WhiteMove[-1] in board_misc:         # if check or mate (mate is also check) Nd6+ or Nd6#
            rank = rank-12
        tune_freq_white = base_freq*(2**((rank-1)/12))
        note_white = create_tone(tune_freq_white,dur,Fs,1)
        tune = np.hstack((tune,note_white))
        tune_white = np.hstack((tune_white,note_white))

        # for black pieces, the 8th rank is considered as starting point
        if BlackMove!=None:
            if BlackMove[0] in board_piece:
                base_freq = piece_freq_black[board_piece.index(BlackMove[0])+1]
                if BlackMove[2] in board_misc:
                    rank = int(BlackMove[4])+12
                elif BlackMove[2] in board_file:
                    rank = int(BlackMove[3])
                    if BlackMove[1] in board_misc:
                        rank = rank+12
                else:
                    rank = int(BlackMove[2])
            
            else:
                if BlackMove[0] in board_misc:
                    base_freq = piece_freq_black[5]           # if castled, the king move is considered and not rook
                    rank = 8                            # for black, castling happens in 8th rank
                else:
                    base_freq = piece_freq_black[0]
                    if BlackMove[1] in board_misc:
                        rank = int(BlackMove[3])+12
                    else:
                        rank = int(BlackMove[1])
            if BlackMove[-1] in board_misc:         # if check or mate (mate is also check)
                rank = rank-12
            tune_freq_black = base_freq*(2**((rank-1)/12))
            note_black = create_tone(tune_freq_black,dur,Fs,1)
            tune = np.hstack((tune,note_black))
            tune_black = np.hstack((tune_black,note_black))
    return tune_white,tune_black,tune,Fs

# input chess game PGN file
tune_white,tune_black,tune,Fs = ParseChessGame('chess_game10.pgn')

# save the wavefiles
wavfile.write('chess_music10.wav',Fs,tune)
wavfile.write('chess_music10w.wav',Fs,tune_white)
wavfile.write('chess_music10b.wav',Fs,tune_black)












