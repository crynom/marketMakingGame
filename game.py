# %%
import random, os, time, msvcrt, sys

SCALER = 5 # scales difficulty, bots quote based on a range of {SCALER - difficulty} about the EV
QSCALER = [2, 5] # scales the time to quote, a player has {max(QSCALER[0] * (QSCALER[1] - difficulty), QSCALER[0])} seconds to quote
TSCALER = [15, 5] # scales the time to trade, a player has {max(TSCALER[0] * (TSCALER[1] - difficulty), TSCALER[0])}
SLEEP = 3 # time to read stuff before clearing the console
SHOWBOARD = 5 # how long to show the board
BOTUNITMAX = 10

# Things to do:
    # Intelligently scale the spread based on difficulty and the available information. Maybe create a space of possible spreads based on the number of missing cards and difficulty and do a random choice from there.
    # Intelligently scale unit sizing for bots, right now they choose randomly between 0 and BOTUNITMAX

    # fix user pnl calculation and add within spread functionality !!

'''
This is a CLI game and it made for windows... sorry!
Inputs have not been santized and I cannot be bothered to do it!

Game
    Attributes:
        cards
        difficulty
        minSpread
        maxSpread
        numBots
        startingBalance
        cards

Player
    Attributes:
        balance
        bot

Bots will create a spread based on the difficulty, they will choose a random number within some range of the EV and assign that randomly to the bid or offer.
Then the other side of the bid-offer will be assigned by randomly choosing a spread in [minSpread, maxSpread]
Each bot will create a spread for every round. If the market maker's bid is at or above their offer, they will buy in an amount which will scale to the distance from their price. Vice versa for the MM's offer and the bot's bid

'''

# functions

def timedInput(prompt: str, timeout: int):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    endtime = time.monotonic() + timeout
    result = []
    while time.monotonic() < endtime:
        if msvcrt.kbhit():
            result.append(msvcrt.getwche())
            if result[-1] == '\r':
                return ''.join(result[:-1])
        time.sleep(0.04)
    return None

# classes

class Game:

    def __init__(self, cards: int = 3, numRounds: int = 1, difficulty: int = 1, minSpread: int = 1, maxSpread: int = 6, numBots: int = 3, startingBalance: int = 500) -> None:
        self.cards = cards
        self.numRounds = numRounds
        self.difficulty = difficulty
        self.minSpread = minSpread
        self.maxSpread = maxSpread
        self.numBots = numBots
        self.startingBalance = startingBalance
        self.players = [Player(startingBalance, False)] + [Player(startingBalance)] * numBots
        random.shuffle(self.players)
        self.deck = list(range(2,15)) * 4
        self.cardEV = sum(self.deck) / len(self.deck)
        self.cardRepr = {
                11:'J',
                12:'Q',
                13:'K',
                14:'A'
                }
        self.user = [i for i, player in enumerate(self.players) if not player.bot][0]
        self.rounds = {}

        
    def getCards(self) -> list[list[int], list[bool]]:
        '''
        Gets cards for a single round of play.

        '''
        board = [[None] * self.cards, [None] * self.cards]
        deck = self.deck
        for i in range(self.cards):
            board[0][i], board[1][i] = random.choice(deck), random.randint(0,1)
            deck.remove(board[0][i])
        if not board[1].count(0):
            board[1][random.randrange(0, len(board[1]))] = 0
        return board


    def printBoard(self, board: list[list[int], list[bool]], gameStage: int = 0) -> None:
        '''
        Prints the board
        '''
        os.system('cls')
        print('This round we have:\n')
        boardRepr = '\t\t' + ' | '.join(['X' if gameStage == 2 else str(self.cardRepr.get(card, card)) if faceUp or gameStage == 1 else 'X' for card, faceUp in zip(board[0], board[1])])
        print(boardRepr)


    def playRound(self, roundNumber: int) -> None:
        '''
        Logic for a single round of play.
        '''
        board = self.getCards()
        self.printBoard(board, gameStage=0)
        
        numPlayers = len(self.players)
        bots = [i for i in range(numPlayers) if i != self.user]

        quotes = {
                i: self.players[i].getQuote(
                    difficulty = self.difficulty,
                    minSpread = self.minSpread,
                    maxSpread = self.maxSpread,
                    board = board,
                    cardEV = self.cardEV
                ) for i in bots
            }

        maker = roundNumber % numPlayers
        user = self.players[self.user]
        quote = user.getQuote(
                    difficulty = self.difficulty,
                    minSpread = self.minSpread,
                    maxSpread = self.maxSpread,
                    board = board,
                    cardEV = self.cardEV
                ) if maker == self.user else quotes[maker]
        if quote is None: 
            time.sleep(SLEEP)
            return None

        makerProfit = 0
        for i in bots:
            bot = self.players[i]
            if i == maker: continue
            if quotes[i][0] >= quote[1]:
                # long
                botUnits = random.randint(0, BOTUNITMAX)
                botProfit = (sum(board[0]) - quote[1]) * botUnits
                bot.balance += botProfit
                bot.history.append({'action':'buy', 'units':botUnits, 'profit':botProfit})
                makerProfit -= botProfit
            elif quotes[i][1] <= quote[0]:
                # short
                botUnits = random.randint(0, BOTUNITMAX)
                botProfit = (quote[0] - sum(board[0])) * botUnits
                bot.balance += botProfit
                bot.history.append({'action':'sell', 'units':botUnits, 'profit':botProfit})
                makerProfit -= botProfit
        self.players[maker].history.append({'action':'maker', 'units':0, 'profit':makerProfit})

        # user makes market
        if self.user == maker:
            self.printBoard(board, gameStage=1)
            print(f'\nYou quoted {quote[0]} at {quote[1]}.')
            time.sleep(SHOWBOARD + SLEEP)
            user.balance += makerProfit
            return None

        # user trades
        else:
            actionRequest = f'\nThe market maker is quoting {quote[0]} at {quote[1]}\n\nYour balance is {user.balance}\n\nDo you want to [B]uy, [S]ell, or [P]ass? '
            actionInput = timedInput(actionRequest, max(TSCALER[0] * (TSCALER[1] - self.difficulty), TSCALER[0]))
            print()
            action = 'p' if actionInput is None else [char for char in actionInput.lower() if char in ['b', 's', 'p']][0]
        
            if 'p' == action: 
                print('You chose to pass. This round will be skipped.')
                time.sleep(SLEEP)
                user.history.append({'action':'pass', 'units':0, 'profit':0})
                return None
        
            units = int(''.join([char for char in actionInput if char.isnumeric()]))

            if 'b' == action:
                if quote[1] * units > user.balance:
                    print('Ouch! You overshot your balance. You have had 50 units deducted and this round will be skipped.')
                    user.balance -= 50
                    time.sleep(SLEEP)
                    return None
                profit = (quote[1] - sum(board[0])) * units

            elif 's' == action:
                long = False
                if ((sum([card for card, faceUp in zip(board[0], board[1]) if faceUp]) + 14 * board[1].count(0)) - quote[0]) * units > user.balance:
                    print('Ouch! You left yourself open to a negative balance in the worst case scenario. You have had 50 units deducted and this round will be skipped.')
                    user.balance -= 50
                    time.sleep(SLEEP)
                    return None
                profit = (sum(board[0]) - quote[1]) * units
            
            self.players[maker].history[-1]['profit'] -= profit
            
            # this is where we show the cards
            self.printBoard(board, gameStage=1)
            print(actionRequest + actionInput)
            time.sleep(SHOWBOARD)
            self.printBoard(board, gameStage=2)
            print(actionRequest + actionInput)

            userProfit = input('Enter your profit or loss: ')
            if len(userProfit) == 0:
                print('You did not enter your profit or loss. You have been penalized 50 units and have forfeited any gains.')
                user.balance -= 50
                time.sleep(SLEEP)
                return None

            userProfit = int(''.join([d for d in userProfit if d.isnumeric() or d == '-']))
            if userProfit != profit:
                print(f'You miscalculated your profit! You have been penalized 50 units{"" if profit <= 0 else " and have forfeited any gains"}.')
                user.balance -= 50
                user.balance += profit if profit < 0 else 0
                user.history.append({'action':'buy' if action == 'b' else 'sell', 'units':units, 'profit': profit if profit < 0 else 0})
            else:
                user.balance += profit
                user.history.append({'action':'buy' if action == 'b' else 'sell', 'units':units, 'profit': profit})
        
    def printSummary(self):
        # add to this
        print(self.players[self.user].balance)

    def playGame(self) -> None:
        '''
        Runs the game loop
        '''
        print(f'\n{"*"*8} Welcome to the game! {"*"*8}')
        for i in range(self.numRounds * len(self.players)):
            self.playRound(i)
            if self.players[self.user].balance <= 0:
                print('You went for broke! Unlucky!')
                return None
        self.printSummary()




class Player:

    def __init__(self, balance: int, bot: bool = True):
        self.balance = balance
        self.bot = bot
        self.history = []

    def getQuote(self, difficulty: int, minSpread: int, maxSpread: int, board: list[list[int], list[bool]], cardEV: int) -> list[int, int] | None:
        if self.bot: 
            ev = sum([card for card, faceUp in zip(board[0], board[1]) if faceUp]) + cardEV * board[1].count(0)
            oneSide = random.randint(int(ev - (SCALER - difficulty)), int(ev + (SCALER - difficulty))) 
            return [oneSide - random.randint(minSpread, maxSpread), oneSide] if random.choice([0, 1]) else [oneSide, oneSide + random.randint(minSpread, maxSpread)]

        quoteInput = timedInput('\nEnter your quote: ', max(QSCALER[0] * (QSCALER[1] - difficulty), QSCALER[0]))
        if quoteInput is None: 
            print('\nTime ran out! This round will be skipped.')
            return None
        quoteInput = ''.join([char for char in quoteInput if char.isnumeric() or char == ' ']).split(' ')
        quote = [int(q) for q in quoteInput]
        return quote
            
game = Game()
game.playGame()
