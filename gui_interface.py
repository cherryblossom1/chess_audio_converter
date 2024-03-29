import numpy as np
import chess
import chess.pgn as pgn
import chess.svg as svg
import tkinter as tk
from tkinter import filedialog
from time import sleep, time
import pygame
from PIL import ImageTk, Image
from cairosvg import svg2png
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from io import StringIO
import shutil
import os
from scipy.signal import butter, lfilter, firls

fname=''
sound=None
board=chess.Board()
moves=None
tone_dur=None
Fs = 44100  # sampling frequency
dur = 350  # note duration in milliseconds

def sdelay(R,x):
    L = x.shape[0]
    b = np.sinc(np.arange(L) - R)
    y = lfilter(b,[1],x)
    return y

def reverb(R,alpha,x):
    b=np.hstack([alpha,np.zeros(R-2),1])
    a=np.hstack([1,np.zeros(R-2),alpha])
    y = lfilter(b,a,x)
    return y

def guitar_filt(freq,samples,x):
    a = np.hstack([1,np.zeros(samples),[-0.5,-0.5]])
    y = lfilter([1],a,x)
    return y

def create_detuned_pulse(freq, dur, Fs, A, num_oscillators, minor):
    # Generate multiple detuned pulse wave oscillators
    tones = []
    if num_oscillators==2:
        detune_factor = [1,3/2]
    elif num_oscillators==3:
        detune_factor = [1,5/4*(1-minor) + 6/5*minor,3/2]
    elif num_oscillators==4:
        detune_factor = [1,5/4*(1-minor) + 6/5*minor,3/2,15/8*(1-minor) + 7/4*minor]
    else:
        detune_factor = [1]
    
    offset=400                          # offset in milliseconds
    for i in range(num_oscillators):
        detuned_freq = freq*detune_factor[i]                            # Generate harmonics
        
        # Generate pulse wave oscillator
        samples = int(Fs / detuned_freq)
        cycles = int(detuned_freq*dur/1000)
        #pulse_table = A/num_oscillators*(np.hstack((np.ones(samples//2), -1*np.ones(samples//2))))
        #triagTable = A/num_oscillators*np.hstack((np.linspace(1,-1,int(samples/2)),np.linspace(-1,1,int(samples/2))))
        #randTable = A/num_oscillators*np.random.randn(samples)
        impulse = A/num_oscillators*np.hstack([1,np.zeros(samples*cycles-1)])
        
        # turn into guitar sound
        #pulse = guitar_filt(detuned_freq,samples,np.tile(triagTable, cycles))
        pulse = guitar_filt(detuned_freq,samples,impulse)
        
        # add reverb
        #pulse = reverb(2,0.9,pulse)
        
        # add delay
        pulse = sdelay(Fs/offset*i,pulse)
        
        tones.append(pulse)
    # Combine the detuned oscillators
    tone = np.zeros(np.max([i.shape for i in tones]))
    for i in range(num_oscillators):
        tone[:tones[i].shape[0]] += tones[i]
    
    return tone

def parse_chess_board(fname,Fs,dur):
    # setup parameters
    board_piece=['R','N','B','Q','K']
    board_file=chess.FILE_NAMES
    board_rank=chess.RANK_NAMES
    board_misc=['x','-','O','#','+']
    
    # in order: pawn, rook, knight, bishop, queen, king
    piece_freq=[175,220,131,165,195,247]
    #piece_freq = 220*(2**((np.random.choice(36,6,replace=False)-1)/12))
    
    # open game and detect moves
    pgn_test = open(fname, encoding='utf-8')
    game = pgn.read_game(pgn_test)
    board = game.board()
    moves = list(game.mainline_moves())
    pgn_moves = []
    for ind,move in enumerate(moves):
        san_move = board.san(move)
        pgn_moves.append(san_move)
        board.push(move)
        svg_data = svg.board(board, size=200)
        svg2png(bytestring=svg_data, write_to=f'./.gallery/board_{ind}.png')
    
    tune=np.array([])
    tone_dur = np.zeros(len(moves))
    for ind,move in enumerate(pgn_moves):
        rank=0
        if move[0] in board_piece:                      # piece move like Nf6, Ndf6, Nxf6, or Ndxf6
            base_freq = piece_freq[board_piece.index(move[0])+1]
            if move[2] in board_misc:                   # capture like Ndxf6
                rank = int(move[4])+12                  # if captures than double the freq
            elif move[2] in board_file:                 # piece move like Ndf6 or capture like Nxf6
                rank = int(move[3])
                if move[1] in board_misc:               # if captures than double the freq
                    rank += 12
            else:                                       # piece move like Nf6
                rank = int(move[2])
            
        else:
            if move[0] in board_misc:                   # castle O-O or O-O-O
                base_freq = piece_freq[5]               # if castled, the king move is considered and not rook
                rank = 7*(ind%2)+1                      # for white, castling happens in 1st rank, and for black castling happens in 8th rank
            else:                                       # pawn move like e4 or exd6
                base_freq = piece_freq[0]
                if move[1] in board_misc:               # pawn capture like exd6 (capture -> double the freq)
                    rank = int(move[3])+12
                else:                                   # normal pawn move like e4
                    rank = int(move[1])

        if move[-1] in board_misc:                      # if check or mate (mate is also check) Nd6+ or Nd6#
            rank -= 12                              # half the freq if check
        tune_freq = base_freq*(2**((rank-1)/12))
        #note = create_tone(tune_freq,dur,Fs,1,waveform='pulse',duty_cycle=0.7)
        note = create_detuned_pulse(freq=tune_freq, dur=dur, Fs=Fs, A=1, num_oscillators=3, minor=0)
        
        # Overlap the note with the previous note using crossfade
        if ind > 0:
            crossfade_samples = int(0.03 * Fs)  # Length of the crossfade region (10% of note duration)
            tune[-crossfade_samples:] *= np.linspace(1.0, 0.0, crossfade_samples)  # Fade out the end of the previous note
            note[:crossfade_samples] *= np.linspace(0.0, 1.0, crossfade_samples)  # Fade in the beginning of the current note
        tune = np.concatenate((tune, note))
        tone_dur[ind] = note.shape[0]/Fs*1000
    return tune,tone_dur,game,board,moves

# prompt for filepath
def get_filepath():
    global fname
    filepath = filedialog.askopenfilename()
    fname=filepath

# parse the board and generate pygame handles
def exec_parse_board():
    global fname, sound, board, moves, Fs, dur, tone_dur, text
    text.delete(1.0,tk.END)
    text.insert(tk.END,'Parsing...')
    if not os.path.isdir('./.gallery'):
        os.makedirs('./.gallery')                        # make a hidden directory if not present
    try:
        if not fname:
            raise ValueError('No file selected.')
        
        tune, tone_dur, game, board, moves = parse_chess_board(fname, Fs, dur)
        pygame.init()
        pygame.mixer.init(frequency=Fs, size=-16, channels=2, buffer=4096)
        tnote = np.outer(tune, [1, 1])
        tnote = tnote * 32767 / np.max(np.abs(tnote))
        tnote = tnote.astype(np.int16)
        sound = pygame.sndarray.make_sound(tnote)
    except ValueError as e:
        print('Error:', str(e))
    text.insert(tk.END,'Done!')

# play the sound and show the board
def play_board():
    global sound, board, moves, dur, image_widget, tone_dur
    if sound is not None:
        board.reset()
        svg_data = svg.board(board, size=200)
        for ind,move in enumerate(moves):
            board.push(move)
            if not ind:
                sound.play()                # start playing at the first move only
            image_widget.delete('all')
            image = Image.open(f'./.gallery/board_{ind}.png')
            tk_image = ImageTk.PhotoImage(image)
            image_widget.create_image(0, 0, anchor=tk.NW, image=tk_image)
            image_widget.update()
            sleep(tone_dur[ind]/1000)
            svg_data = svg.board(board, size=200)


# Create a function to quit the program
def quit_program():
    global sound
    if window is not None:
        window.quit()
        window.destroy()
    if sound is not None:
        sound.stop()
    if os.path.isdir('./.gallery'):
        shutil.rmtree('./.gallery')

# Create the main window
window = tk.Tk()

# Set the window title
window.title('File Selection')

# Set the window size
window.geometry('640x400')  # Width: 600 pixels, Height: 400 pixels

# Create a button to open a file dialog
button = tk.Button(window, text='Select File', command=get_filepath)
button.grid(row=0, column=0, padx=10, pady=0, sticky='w')

# Create a button to parse the board
button2 = tk.Button(window, text='Parse', command=exec_parse_board)
button2.grid(row=1, column=0, padx=10, pady=0, sticky='w')

# Create a button to play
button3 = tk.Button(window, text='Play', command=play_board)
button3.grid(row=2, column=0, padx=10, pady=0, sticky='w')

# Create a button to quit the program
quit_button = tk.Button(window, text='Quit', command=quit_program)
quit_button.grid(row=3, column=0, padx=10, pady=0, sticky='w')

# Create a text widget to display text content
text = tk.Text(window, height=1, width=20)
text.grid(row=0, column=1, padx=0, pady=0)

# Create an image widget to display the PNG image
image_widget = tk.Canvas(window, width=200, height=200, bg='white')
image_widget.grid(row=1, column=1, padx=10, pady=0)

# Configure grid weights to make the text widget expand to fill the available space
window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(1, weight=1)

# Run the main event loop
window.mainloop()





