#! python3

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


# Create the global grid data structure. GRID[x][y] contains None for empty
# space or an RGB triplet. The grid is the shared data structure that the worms
# write data to, and since each worm runs in a separate thread we will have to
# add locks so that the worms don't step over each other when checking and
# updating the values in this shared data structure.
#
# If we were not using threads, then it would be impossible for the worms
# to step over each other since their code would always be executing in
# normal order. (But then our program wouldn't be multithreaded.)
GRID = []
for x in range(CELLS_WIDE):
    GRID.append([None] * CELLS_HIGH)

GRID_LOCKS = [] # pun was not intended
for x in range(CELLS_WIDE):
    column = []
    for y in range(CELLS_HIGH):
        column.append(threading.Lock()) # create one Lock object for each cell
    GRID_LOCKS.append(column)

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

# Constants for the four cardinal directions, because a mistyped variable
# like DWON will cause an immediate NameError crash and be easy to spot. But a
# mistyped string like 'dwon' is still syntactically valid Python code, so
# it will cause bugs that might be hard to track down.
UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

# Since the data structure for a worm's body segments is a list
# where the "head" is the first item in the list, we can use
# HEAD as the index.
HEAD = 0

# In queues in computer science, the "tail" often doesn't refer to the last
# item but rather *every* item after the head. So I'll use "butt" to refer
# to the index of the last body segment for a worm.
BUTT = -1 # negative indexes count from the end, so -1 will always be the last index

# A global variable that the Worm threads check to see if they should exit.
WORMS_RUNNING = True

class Worm(threading.Thread): # "Thread" is a class in the "threading" module.
    def __init__(self, name='Worm', maxsize=None, color=None, speed=20):
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

        # The body starts as a single segment at a random location (but make sure
        # it is unoccupied.)
        # As the worm begins to move, new segments will be added until it reaches full length.
        while True:
            startx = random.randint(0, CELLS_WIDE - 1)
            starty = random.randint(0, CELLS_HIGH - 1)
            # This thread will wait until the Lock in GRID_LOCKS is released
            # (if it is currently acquired by a different thread). If another thread
            # has currently acquired the lock, the acquire() call will not return
            # (i.e. it will "block") until the lock is released by that other thread.
            # (There may be a queue of threads that are currently waiting to acquire
            # the lock, and they might be selected to run first. In that case, we
            # have to wait until _they_ call release().)
            GRID_LOCKS[startx][starty].acquire() # block until this thread can acquire the lock
            if GRID[startx][starty] is None:
                break # we've found an unoccupied cell in the grid

        GRID[startx][starty] = self.color # modify the shared data structure

        # Now that we're done modifying the data structure that is shared
        # by all the threads (i.e. GRID), we can release the lock so that
        # other threads can acquire it.
        GRID_LOCKS[startx][starty].release()

        # The worm's body starts as a single segment, and keeps growing until it
        # reaches full length. This makes setup easier.
        self.body = [{'x': startx, 'y': starty}]
        self.direction = random.choice((UP, DOWN, LEFT, RIGHT))


    def run(self):
        # Note that this thread's code only updates GRID, which is the variable
        # that tracks which cells have worm body segments and which are free.
        # Nothing in this thread draws pixels to the screen. So we could have this
        # code run separate from the visualization of the worms entirely!
        #
        # This means that instead of the Pygame grid display, we could write
        # code that displays the worms in 3D without changing the Worm class's
        # code at all. The visualization code just has to read the GRID variable
        # (in a thread-safe manner by using GRID_LOCKS, of course).
        while True:
            if not WORMS_RUNNING:
                return # A thread terminates when run() returns.

            # Randomly decide to change direction
            if random.randint(0, 100) < 20: # 20% to change direction
                self.direction = random.choice((UP, DOWN, LEFT, RIGHT))

            nextx, nexty = self.getNextPosition()

            # We are going to make modifications to GRID, so we need to acquire
            # the lock first.
            origx, origy = nextx, nexty
            if origx not in (-1, CELLS_WIDE) and origy not in (-1, CELLS_HIGH):
                gotLock = GRID_LOCKS[origx][origy].acquire(timeout=1) # don't return (that is, block) until this thread can acquire the lock
                if not gotLock:
                    continue

            # Really, we should check if nextx < 0 or nextx >= CELLS_WIDE, but
            # since worms only move one space at a time, we can get away with
            # just checking if they are at -1 or CELLS_WIDE/CELLS_HIGH.
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
            if origx not in (-1, CELLS_WIDE) and origy not in (-1, CELLS_HIGH):
                GRID_LOCKS[origx][origy].release()


            if self.direction is not None:
                GRID_LOCKS[nextx][nexty].acquire()
                # Space on the grid is free, so move there.
                GRID[nextx][nexty] = self.color # update the GRID state
                GRID_LOCKS[nextx][nexty].release()
                self.body.insert(0, {'x': nextx, 'y': nexty}) # update this worm's own state

                # Check if we've grown too long, and cut off tail if we have.
                # This gives the illusion of the worm moving.

                # TODO - here's where our bug is. Sometimes the worms are still growing but they run into each other. This is what holds up their threads.
                if len(self.body) > self.maxsize:
                    # TODO - something weird is going on here. Doing the sepukku routine lets us quit cleanly, but the worm still appears drawn on the screen.
                    gotLock = GRID_LOCKS[self.body[BUTT]['x']][self.body[BUTT]['y']].acquire(timeout=2)
                    if not gotLock:
                        self.maxsize -= 1 # TODO - not entirely sure why this imrpoves the framerate.
                        #print('chop %s' % (self.name))
                    GRID[self.body[BUTT]['x']][self.body[BUTT]['y']] = None # update the GRID state
                    GRID_LOCKS[self.body[BUTT]['x']][self.body[BUTT]['y']].release()
                    del self.body[BUTT] # update this worm's own state (heh heh, worm butt)
            else:
                self.direction = random.choice((UP, DOWN, LEFT, RIGHT)) # can't move, so just do nothing for now but set a new random direction

            # On a technical note, a worm could get stuck inside itself if its
            # head and butt are in this pattern:
            #
            # With lines:    Where "A" is the head and "L" is the butt:
            #    /\/\              CBKJ
            #    |HB|              DALI
            #    \--/              EFGH
            # I call this a worm knot. I left my computer running with 24 worms
            # moving with 0 speed overnight, but I didn't see any of these worm
            # knots form, so I'm guessing it is super rare.

            # Pygame's pygame.time.wait() and the Python Standard Library's
            # time.time() functions (and the tick() method) are smart enough
            # to tell the operating system to put the thread to sleep for a
            # while and just run other threads instead. Of course, while the
            # OS could interrupt our thread at any time to hand execution off
            # to a different thread, calling wait() or sleep() is a way we can
            # explicitly say, "Go ahead and don't run this thread for X
            # milliseconds."
            #
            # This wouldn't happen if we have "wait" code like this:
            # startOfWait = time.time()
            # while time.time() - 5 > startOfWait:
            #     pass # do nothing for 5 seconds
            #
            # The above code also implements "waiting", but to the OS it looks
            # like your thread is still executing code (even though this code
            # is doing nothing but looping until 5 seconds has passed).
            # This is inefficient, because time spent executing the above pointless
            # loop is time that could have been spent executing other thread's
            # code.
            # Of course, if ALL worms' threads are sleeping, then the computer
            # can know it can use the CPU to run other programs besides
            # our Python Threadworms script.
            pygame.time.wait(self.speed)

            # The beauty of using multiple threads here is that we can have
            # the worms move at different rates of speed just by passing a
            # different integer to wait().
            # If we did this program in a single thread, we would have to
            # calculate how often we update the position of each worm based
            # on their speed relative to all the other worms, which would
            # be a headache. But now we have the threads doing this work
            # for us!


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

        # Remember that nextx & nexty could be invalid (by referring to a location
        # on the grid already taken by a body segment or beyond the boundaries
        # of the window.)
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
        worms.append(Worm(name='Worm %s' % i))
        worms[-1].start() # Start the worm code in its own thread.

    DISPLAYSURF.fill(BGCOLOR)
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
    for x in range(0, WINDOWWIDTH, CELL_SIZE): # draw vertical lines
        pygame.draw.line(DISPLAYSURF, GRID_LINES_COLOR, (x, 0), (x, WINDOWHEIGHT))
    for y in range(0, WINDOWHEIGHT, CELL_SIZE): # draw horizontal lines
        pygame.draw.line(DISPLAYSURF, GRID_LINES_COLOR, (0, y), (WINDOWWIDTH, y))

    # The main thread that stays in the main loop (which calls drawGrid) also
    # needs to acquire the GRID_LOCKS lock before modifying the GRID variable.

    for x in range(0, CELLS_WIDE):
        for y in range(0, CELLS_HIGH):
            gotLock = GRID_LOCKS[x][y].acquire(timeout=0.02)
            if not gotLock:
                # If we can't acquire the lock for this cell, don't draw anything and just leave it as it is.
                continue

            if GRID[x][y] is None:
                # No body segment at this cell to draw, so draw a blank square
                pygame.draw.rect(DISPLAYSURF, BGCOLOR, (x * CELL_SIZE + 1, y * CELL_SIZE + 1, CELL_SIZE - 1, CELL_SIZE - 1))
                GRID_LOCKS[x][y].release() # We're done reading GRID, so release the lock.
            else:
                color = GRID[x][y] # read the GRID data structure
                GRID_LOCKS[x][y].release() # We're done messing with GRID, so release the lock.

                # Draw the body segment on the screen
                darkerColor = (max(color[0] - 50, 0), max(color[1] - 50, 0), max(color[2] - 50, 0))
                pygame.draw.rect(DISPLAYSURF, darkerColor, (x * CELL_SIZE,     y * CELL_SIZE,     CELL_SIZE,     CELL_SIZE    ))
                pygame.draw.rect(DISPLAYSURF, color,       (x * CELL_SIZE + 4, y * CELL_SIZE + 4, CELL_SIZE - 8, CELL_SIZE - 8))


def setGridSquares(squares, color=(192, 192, 192)):
    # "squares" is a multiline string that has '.' to express "no change", a
    # ' ' space to set the cell to be empty, and any other character will
    # set the space with the value in "color"
    # Blank lines in squares are ignored for the first and last line, to make
    # typing the string easier.
    #
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

    for y in range(min(len(squares), CELLS_HIGH)):
        for x in range(min(len(squares[y]), CELLS_WIDE)):
            GRID_LOCKS[x][y].acquire()
            if squares[y][x] == ' ':
                GRID[x][y] = None
            elif squares[y][x] == '.':
                pass
            else:
                GRID[x][y] = color
            GRID_LOCKS[x][y].release()


if __name__ == '__main__':
    main()