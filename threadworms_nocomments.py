# Threadworms (a Python/Pygame threading demonstration)
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/blog
# Released under a "Simplified BSD" license

# This is meant to be an educational example of multithreaded programming,
# so I get kind of verbose in the comments.

import random, pygame, sys, threading
from pygame.locals import *

# Setting up constants
NUM_WORMS = 24  # the number of worms in the grid
FPS = 30        # frames per second that the program runs
CELL_SIZE = 20  # how many pixels wide and high each "cell" in the grid is
CELLS_WIDE = 32 # how many cells wide the grid is
CELLS_HIGH = 24 # how many cells high the grid is


GRID = []
for x in range(CELLS_WIDE):
    GRID.append([None] * CELLS_HIGH)

GRID_LOCK = threading.Lock() # pun was not intended

# Constants for some colors.
#             R    G    B
WHITE     = (255, 255, 255)
BLACK     = (  0,   0,   0)
DARKGRAY  = ( 40,  40,  40)
BGCOLOR = BLACK             # color to use for the background of the grid
GRID_LINES_COLOR = DARKGRAY # color to use for the lines of the grid

# Calculate total pixels wide and high that the full window is
WINDOWWIDTH = CELL_SIZE * CELLS_WIDE
WINDOWHEIGHT = CELL_SIZE * CELLS_HIGH

UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

HEAD = 0
BUTT = -1 # negative indexes count from the end, so -1 will always be the last index

# A global variable that the Worm threads check to see if they should exit.
WORMS_RUNNING = True

class Worm(threading.Thread): # "Thread" is a class in the "threading" module.
    def __init__(self, name='Worm', maxsize=None, color=None, speed=None):
        # name can be used for debugging purposes. It will appear in any thrown exceptions so you can tell which thread crashed.
        # maxsize is the length of the worm (in body segments).
        # color is an RGB tuple for the worm. The darker shade is automatically calculated.
        # speed is an integer of milliseconds the worm waits after moving once. 1000=move once a second, 0=move as fast as possible

        threading.Thread.__init__(self) # since we are overriding the Thread class, we need to first call its __init__() method.

        self.name = name

        # Set the maxsize to the parameter, or to a random maxsize.
        if maxsize is None:
            self.maxsize = random.randint(4, 10)

            # Have a small chance of a super long worm.
            if random.randint(0,4) == 0:
                self.maxsize += random.randint(10, 20)
        else:
            self.maxsize = maxsize

        # Set the color to the parameter, or to a random color.
        if color is None:
            self.color = (random.randint(60, 255), random.randint(60, 255), random.randint(60, 255))
        else:
            self.color = color

        # Set the speed to the parameter, or to a random number.
        if speed is None:
            self.speed = random.randint(20, 500) # wait time before movements will be between 0.02 and 0.5 seconds
        else:
            self.speed = speed

        GRID_LOCK.acquire() # block until this thread can acquire the lock

        while True:
            startx = random.randint(0, CELLS_WIDE - 1)
            starty = random.randint(0, CELLS_HIGH - 1)
            if GRID[startx][starty] is None:
                break # we've found an unoccupied cell in the grid

        GRID[startx][starty] = self.color # modify the shared data structure

        GRID_LOCK.release()

        # The worm's body starts as a single segment, and keeps growing until it
        # reaches full length. This makes setup easier.
        self.body = [{'x': startx, 'y': starty}]
        self.direction = random.choice((UP, DOWN, LEFT, RIGHT))


    def run(self):
        while True:
            if not WORMS_RUNNING:
                return # A thread terminates when run() returns.

            # Randomly decide to change direction
            if random.randint(0, 100) < 20: # 20% to change direction
                self.direction = random.choice((UP, DOWN, LEFT, RIGHT))

            GRID_LOCK.acquire() # don't return (that is, block) until this thread can acquire the lock

            nextx, nexty = self.getNextPosition()
            if nextx in (-1, CELLS_WIDE) or nexty in (-1, CELLS_HIGH) or GRID[nextx][nexty] is not None:
                # The space the worm is heading towards is taken, so find a new direction.
                self.direction = self.getNewDirection()

                if self.direction is None:
                    # No places to move, so try reversing our worm.
                    self.body.reverse() # Now the head is the butt and the butt is the head. Magic!
                    self.direction = self.getNewDirection()

                if self.direction is not None:
                    # It is possible to move in some direction, so reask for the next postion.
                    nextx, nexty = self.getNextPosition()

            if self.direction is not None:
                # Space on the grid is free, so move there.
                GRID[nextx][nexty] = self.color # update the GRID state
                self.body.insert(0, {'x': nextx, 'y': nexty}) # update this worm's own state

                # Check if we've grown too long, and cut off tail if we have.
                # This gives the illusion of the worm moving.
                if len(self.body) > self.maxsize:
                    GRID[self.body[BUTT]['x']][self.body[BUTT]['y']] = None # update the GRID state
                    del self.body[BUTT] # update this worm's own state (heh heh, worm butt)
            else:
                self.direction = random.choice((UP, DOWN, LEFT, RIGHT)) # can't move, so just do nothing for now but set a new random direction

            GRID_LOCK.release()

            pygame.time.wait(self.speed)


    def getNextPosition(self):
        # Figure out the x and y of where the worm's head would be next, based
        # on the current position of its "head" and direction member.

        if self.direction == UP:
            nextx = self.body[HEAD]['x']
            nexty = self.body[HEAD]['y'] - 1
        elif self.direction == DOWN:
            nextx = self.body[HEAD]['x']
            nexty = self.body[HEAD]['y'] + 1
        elif self.direction == LEFT:
            nextx = self.body[HEAD]['x'] - 1
            nexty = self.body[HEAD]['y']
        elif self.direction == RIGHT:
            nextx = self.body[HEAD]['x'] + 1
            nexty = self.body[HEAD]['y']
        else:
            assert False, 'Bad value for self.direction: %s' % self.direction

        return nextx, nexty


    def getNewDirection(self):
        x = self.body[HEAD]['x'] # syntactic sugar, makes the code below more readable
        y = self.body[HEAD]['y']

        # Compile a list of possible directions the worm can move.
        newDirection = []
        if y - 1 not in (-1, CELLS_HIGH) and GRID[x][y - 1] is None:
            newDirection.append(UP)
        if y + 1 not in (-1, CELLS_HIGH) and GRID[x][y + 1] is None:
            newDirection.append(DOWN)
        if x - 1 not in (-1, CELLS_WIDE) and GRID[x - 1][y] is None:
            newDirection.append(LEFT)
        if x + 1 not in (-1, CELLS_WIDE) and GRID[x + 1][y] is None:
            newDirection.append(RIGHT)

        if newDirection == []:
            return None # None is returned when there are no possible ways for the worm to move.

        return random.choice(newDirection)

def main():
    global FPSCLOCK, DISPLAYSURF

    # Draw some walls on the grid
    squares = """
...........................
...........................
...........................
.H..H..EEE..L....L.....OO..
.H..H..E....L....L....O..O.
.HHHH..EE...L....L....O..O.
.H..H..E....L....L....O..O.
.H..H..EEE..LLL..LLL...OO..
...........................
.W.....W...OO...RRR..MM.MM.
.W.....W..O..O..R.R..M.M.M.
.W..W..W..O..O..RR...M.M.M.
.W..W..W..O..O..R.R..M...M.
..WW.WW....OO...R.R..M...M.
...........................
...........................
"""
    #setGridSquares(squares)

    # Pygame window set up.
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.display.set_caption('Threadworms')

    # Create the worm objects.
    worms = [] # a list that contains all the worm objects
    for i in range(NUM_WORMS):
        worms.append(Worm())
        worms[-1].start() # Start the worm code in its own thread.

    while True: # main game loop
        handleEvents()
        drawGrid()

        pygame.display.update()
        FPSCLOCK.tick(FPS)


def handleEvents():
    # The only event we need to handle in this program is when it terminates.
    global WORMS_RUNNING

    for event in pygame.event.get(): # event handling loop
        if (event.type == QUIT) or (event.type == KEYDOWN and event.key == K_ESCAPE):
            WORMS_RUNNING = False # Setting this to False tells the Worm threads to exit.
            pygame.quit()
            sys.exit()


def drawGrid():
    # Draw the grid lines.
    DISPLAYSURF.fill(BGCOLOR)
    for x in range(0, WINDOWWIDTH, CELL_SIZE): # draw vertical lines
        pygame.draw.line(DISPLAYSURF, GRID_LINES_COLOR, (x, 0), (x, WINDOWHEIGHT))
    for y in range(0, WINDOWHEIGHT, CELL_SIZE): # draw horizontal lines
        pygame.draw.line(DISPLAYSURF, GRID_LINES_COLOR, (0, y), (WINDOWWIDTH, y))

    # The main thread that stays in the main loop (which calls drawGrid) also
    # needs to acquire the GRID_LOCK lock before modifying the GRID variable.
    GRID_LOCK.acquire()

    for x in range(0, CELLS_WIDE):
        for y in range(0, CELLS_HIGH):
            if GRID[x][y] is None:
                continue # No body segment at this cell to draw, so skip it

            color = GRID[x][y] # modify the GRID data structure

            # Draw the body segment on the screen
            darkerColor = (max(color[0] - 50, 0), max(color[1] - 50, 0), max(color[2] - 50, 0))
            pygame.draw.rect(DISPLAYSURF, darkerColor, (x * CELL_SIZE,     y * CELL_SIZE,     CELL_SIZE,     CELL_SIZE    ))
            pygame.draw.rect(DISPLAYSURF, color,       (x * CELL_SIZE + 4, y * CELL_SIZE + 4, CELL_SIZE - 8, CELL_SIZE - 8))

    GRID_LOCK.release() # We're done messing with GRID, so release the lock.


def setGridSquares(squares, color=(192, 192, 192)):
    # squares is set to a value like:
    # """
    # ......
    # ...XX.
    # ...XX.
    # ......
    # """

    squares = squares.split('\n')
    if squares[0] == '':
        del squares[0]
    if squares[-1] == '':
        del squares[-1]

    GRID_LOCK.acquire()
    for y in range(min(len(squares), CELLS_HIGH)):
        for x in range(min(len(squares[y]), CELLS_WIDE)):
            if squares[y][x] == ' ':
                GRID[x][y] = None
            elif squares[y][x] == '.':
                pass
            else:
                GRID[x][y] = color
    GRID_LOCK.release()


if __name__ == '__main__':
    main()