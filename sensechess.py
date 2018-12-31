import chess
import pisense
from colorzero import Color, Red, Blue, Green
from time import sleep
import chess.uci

board = chess.Board()
human_players = 1
move_time = 200
engine = chess.uci.popen_engine("stockfish")
engine.uci()
print('engine name: {}'.format(engine.name))

hat = pisense.SenseHAT()
"""
hat.screen represents the 8 x 8 grid of LEDs on the HAT.
hat.stick represents the miniature joystick at the bottom right of the HAT.
hat.environ represents the environmental (pressure, humidity and temperature) sensors on the HAT.
hat.imu represents the sensors of the Internal Measurement Unit (IMU) on the HAT.
"""
stick = hat.stick
in_flash = False

cPieces = {False: 'rnbqkp', True: 'PRNBQK'}

brightness = 0.2

# Dictionary to map pieces to Sense HAT colours
ColMap = {
  #red
  'p': Color.from_rgb_bytes(64, 16, 0),
  'n': Color.from_rgb_bytes(112, 32, 0),
  'b': Color.from_rgb_bytes(160, 48, 0),
  'r': Color.from_rgb_bytes(192, 64, 0),
  'q': Color.from_rgb_bytes(224, 96, 0),
  'k': Color.from_rgb_bytes(255, 128, 0),
  #blue
  'P': Color.from_rgb_bytes(0, 16, 64),
  'N': Color.from_rgb_bytes(0, 33, 112),
  'B': Color.from_rgb_bytes(0, 48, 160),
  'R': Color.from_rgb_bytes(0, 64, 192),
  'Q': Color.from_rgb_bytes(0, 96, 224),
  'K': Color.from_rgb_bytes(0, 128, 255)
}

# Screen position of the cursor
x = None
Y = None

""" Modes:
None - no piece selected
Piece - piece selected
Move - valid move selected
"""
mode = None
# Chess move position created from selected x, y
mv_from = None
mv_to = None


def empty_screen_board():
  # return an empty board for PiSense
  return pisense.array([
    Color(h=0.0, s=0.0, v=((x+y+1)%2) * brightness)
    for x in range(8)
    for y in range(8)
    ])

def draw_board(esb, fen):
  """
  Draw pieces on the screen board

  esb is an empty PiSense screen board, e.g. just the checker pattern
  fen example 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

  return a drawn board
  """
  sb = esb.copy()
  bs = fen.split('/')
  bs[7] = bs[7][:8]
  for row,r in enumerate(bs):
    col = 0
    for c in r:
      if c in ColMap:
        #print('row={}, col={}, c={}'.format(row, col, c))
        sb[row, col] = ColMap[c]
        col += 1
      else:
        if c == ' ': print('c={} r={}'.format(c, r))
        col += int(c)
      if col >= 8:
        break
  return sb


def flash(sb):
  global in_flash
  if in_flash: return
  in_flash = True
  fx, fy = x, y
  fsquare = chess.square(fx, 7-fy)
  fpiece = board.piece_at(fsquare)
  
  if mv_from is None:
    # no piece selected
    if fpiece is None:
      # flash to inverted board
      flash_colour = Color(h=0.0, s=0.0, v=((fx+fy)%2)*brightness)
    else:
      #flash to underlying board
      flash_colour = Color(h=0.0, s=0.0, v=((fx+fy+1)%2)*brightness)
  else:
    piece = board.piece_at(mv_from)
    if piece is None:
      #piece has moved
      piece = board.piece_at(mv_to)
    flash_colour = ColMap[piece.symbol()]
    show_moves(sb, piece, mv_from)
  sb[fy, fx] = flash_colour
  hat.screen.array = sb
  sleep(0.1)
  
  fpiece = board.piece_at(fsquare)
  if fpiece is None:
    board_colour = Color(h=0.0, s=0.0, v=((fx+fy+1)%2)*brightness)
  else:
    board_colour = ColMap[fpiece.symbol()]
  sb[fy, fx] = board_colour
  hat.screen.array = sb
  
  in_flash = False


def show_moves(sb, piece, square):
  # shade green all the positions for this piece from this square
  squares = []
  for m in board.legal_moves:
    if m.from_square == square:
      squares.append(m.to_square)
  print('squares={}'.format(squares))
  for s in squares:
    sr = int((s-1) / 8)
    sx = (s-1) - int(s/8)*8+1
    sy = 7-sr
    print('s={} sy={} sx={}'.format(s, sy, sx))
    print('sb at sy,sx={}'.format(sb[sy, sx]))
    sb[sy, sx] = Color.from_rgb(sb[sy, sx][0], 0.3, sb[sy, sx][2])

mm_clip = lambda x, l, u: max(l, min(u, x))

def moved(event):
  #StickEvent(timestamp, direction, pressed, held)
  global x, y
  #print('pressed={} held={}'.format(event.pressed, event.held))
  if event.pressed and not event.held:
    #print('move start', x, y)
    try:
      nx = x + {
        'left':  (-1, 0),
        'right': (1, 0),
        'up':    (0, -1),
        'down':  (0, 1),
        }[event.direction][0]
      ny = y + {
        'left':  (-1, 0),
        'right': (1, 0),
        'up':    (0, -1),
        'down':  (0, 1),
        }[event.direction][1]
      x = mm_clip(nx, 0, 7)
      y = mm_clip(ny, 0, 7)
    except KeyError:
      pass # ignore enter


def click(event):
  #StickEvent(timestamp, direction, pressed, held)
  global mv_from, mv_to, mode
  if mode is not 'Move':
    #print('pressed={} held={}'.format(event.pressed, event.held))
    if event.pressed and not event.held:
      print('mode={} x={} y={}'.format(mode, x, y))
      square = chess.square(x, 7-y)
      print('square={}'.format(square))
      if mode is None:
        #is it a valid piece
        piece = board.piece_at(square)
        print('piece={} turn={}'.format(piece, board.turn))
        #print('pieces={}'.format(cPieces[board.turn]))
        if piece is not None and piece.symbol() in cPieces[board.turn]:
          #print('symbol={}'.format(piece.symbol()))
          #print('type={} color={}'.format(piece.piece_type, piece.color))
          mode = 'Piece'
          mv_from = square
          print('mode={} x={} y={}'.format(mode, x, y))
      elif mode == 'Piece':
        if square == mv_from:
          #clicked back on same sqaure so unselect
          mode = None
          mv_from = None
        else:
          #is valid move
          move = chess.Move(mv_from, square)
          if move in board.legal_moves:
            mv_to = square
            board.push(move)
            mode = 'Move'
            print('mode={} x={} y={}'.format(mode, x, y))
            if board.is_checkmate():
              #turn colour has won
              pass
            elif board.is_stalemate() or board.is_insufficient_material() \
                or board.is_fivefold_repetition():
              # draw
              pass

def test_mate_in_four(esb, board):
  # Test moving and board drawing with a quick mate in four
  test_moves = ['e4','e5','Qh5','Nc6','Bc4','Nf6','Qxf7']
  
  for m in test_moves:
    sleep(1)
    board.push_san(m)
    sb = draw_board(esb, board.fen())
    hat.screen.array = sb


def main():
  global x, y, mode, mv_from, mv_to
  # Display empty board
  esb = empty_screen_board()
  hat.screen.array = esb
  sleep(1)
  
  # Initial cursor position.
  x = 3
  y = 6
  
  # Display board with pieces
  #board = chess.Board()
  #'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
  print(board)
  sb = draw_board(esb, board.fen())
  hat.screen.array = sb
  sleep(1)
  
  stick.when_enter = click
  stick.when_up = moved
  stick.when_down = moved
  stick.when_left = moved
  stick.when_right = moved
  
  while board.result() == '*':
    flash(sb)
    if mode != 'Move':
      sleep(0.1)
    else:
      print(board)
      sb = draw_board(esb, board.fen())
      hat.screen.array = sb
      mode = None
      mv_from = None
      mv_to = None
      if board.result() != '*':
        break
      # Synchronous mode.
      engine.position(board)
      print('go={}'.format(engine.go(movetime=move_time)))
      bestmove, pondermove = engine.go(movetime=move_time)  # Gets a tuple of bestmove and ponder move
      #BestMove(bestmove=Move.from_uci('d6d1'), ponder=Move.from_uci('c1d1'))
      #print('bestmove={} ponder={}'.format(bestmove, pondermove))
      board.push(bestmove)
      print(board)
      sb = draw_board(esb, board.fen())
      hat.screen.array = sb

  mesg = "Error"
  result = board.result()
  if result == '1-0':
    mesg = "White wins"
  elif result == '0-1':
    mesg = "Black wins"
  elif result == '1/2-1/2':
    mesg = "Draw"
  hat.screen.scroll_text(mesg)
  
  sleep(5)
  hat.screen.clear()
  stick.close()
  engine.quit()

main()
#test_mate_in_four(esb, board)

