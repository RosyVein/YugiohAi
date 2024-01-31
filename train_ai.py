import datetime
import glob
import math
import multiprocessing
import os
import random
import shutil
import sqlite3
import string
import subprocess
import sys
import tensorflow as tf
import time
import typing
from keras.layers import Dense, Flatten
from keras.models import Sequential
from keras.models import load_model
from pathlib import Path
from sys import platform
from threading import Thread
import matplotlib.pyplot as plt

import get_action_weights_tensorflow as get_action_weights
import read_data_tensorflow as read_game_data

# The Deck name and location
AI1Deck = 'Random1'
AI2Deck = 'Random2'
AIMaster = 'Master'

deck1 = 'AI_Random1.ydk'
deck2 = 'AI_Random2.ydk'

totalGames = 100  # it is roundlimit!?!?
generations = 100

rolloutCount = 1
isFirst = True
isTraining = True
winThresh = 60
pastWinLim = 5
idNumber = 1

reset = False


def isrespondingPID(PID):
    if platform == "linux" or platform == "linux2":
        return True

    # https://stackoverflow.com/questions/16580285/how-to-tell-if-process-is-responding-in-python-on-windows
    os.system('tasklist /FI "PID eq %d" /FI "STATUS eq running" > tmp.txt' % PID)
    tmp = open('tmp.txt', 'r')
    a = tmp.readlines()
    tmp.close()
    try:
        if int(a[-1].split()[1]) == PID:
            return True
        else:
            return False
    except:
        return False


def deleteData():
    folder = './data'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def resetDB():
    deleteData()
    dbfile = './cardData.cdb'
    con = sqlite3.connect(dbfile)
    cur = con.cursor()
    sql_delete_query = """DELETE from L_ActionList"""
    cur.execute(sql_delete_query)
    sql_delete_query = """DELETE from L_CompareTo"""
    cur.execute(sql_delete_query)
    sql_delete_query = """DELETE from L_PlayRecord"""
    cur.execute(sql_delete_query)
    sql_delete_query = """DELETE from L_FieldState"""
    cur.execute(sql_delete_query)
    sql_delete_query = """DELETE from L_ActionState"""
    cur.execute(sql_delete_query)
    sql_delete_query = """DELETE from L_Weights"""
    cur.execute(sql_delete_query)
    con.commit()
    con.close()


def resetYgoPro():
    print("deleting old deck files from ygopro")
    files = glob.glob(os.getcwd() + "/ProjectIgnis/deck/*")
    for f in files:
        os.remove(f)

    print("deleting old replays from ygopro")
    files = glob.glob(os.getcwd() + "/ProjectIgnis/replay/*")
    for f in files:
        os.remove(f)


def parseArg():
    global reset, isTraining, repeatFor, matches, totalGames, isFirst

    reset = len(sys.argv) > 1 and ("--reset" in sys.argv or "-r" in sys.argv)
    isTraining = len(sys.argv) > 1 and ("--training" in sys.argv or "-t" in sys.argv)
    isFirst = len(sys.argv) > 1 and ("--first" in sys.argv or "-f" in sys.argv)

    print(isTraining)

    if "--repeat" in sys.argv:
        repeatFor = int(sys.argv[sys.argv.index("--repeat") + 1])
    if "--matches" in sys.argv:
        matches = int(sys.argv[sys.argv.index("--matches") + 1])
    if "--games" in sys.argv:
        totalGames = int(sys.argv[sys.argv.index("--games") + 1])


def runAi(Deck="Random1",
          Name="Random1",
          Hand=0,
          TotalGames=1,
          RolloutCount=0,
          IsFirst=True,
          IsTraining=True,
          ShouldUpdate=True,
          WinsThreshold=50,
          PastWinsLimit=20,
          Id=0
          ):
    currentdir = os.getcwd()
    os.chdir(os.getcwd() + '/WindBot-Ignite-master/bin/Debug')

    file_name = "WindBot.exe"

    if platform == "linux" or platform == "linux2":
        file_name = os.getcwd() + "/WindBot.exe"

    p = subprocess.Popen([file_name, "Deck=" + Deck,
                          "Name=" + str(Name),
                          "Hand=" + str(Hand),
                          "IsTraining=" + str(IsTraining),
                          "ShouldUpdate=" + str(ShouldUpdate),
                          # "TotalGames=" + str(TotalGames),
                          "RolloutCount=" + str(RolloutCount),
                          "IsFirst=" + str(IsFirst),
                          "WinsThreshold=" + str(WinsThreshold),
                          "PastWinsLimit=" + str(PastWinsLimit),
                          "Id=" + str(Id)
                          ],
                         stdout=subprocess.DEVNULL)

    os.chdir(currentdir)

    return p


def shuffle_deck(deck_name):
    filePath = os.getcwd() + '/WindBot-Ignite-master/bin/debug/Decks/' + deck_name

    f = open(filePath, "r")
    main = []
    extra = []
    side = []
    part = 0
    for line in f.readlines():
        if "#extra" in line:
            part = 1
            continue
        elif "!side" in line:
            part = 2
            continue
        elif "#main" in line:
            part = 0
            continue
        elif "#" in line:
            continue

        if part == 0:
            main.append(line.strip())
        elif part == 1:
            extra.append(line.strip())
        else:
            side.append(line.strip())
        random.shuffle(main)
        random.shuffle(extra)
        random.shuffle(side)

    f.close()

    f = open(filePath, "w")
    # f.write("#created by deck_maker_ai\n")

    f.write("#main\n")
    for i in main:
        f.write(i + '\n')
    f.write("#extra\n")
    for i in extra:
        f.write(i + '\n')
    f.write("!side\n")
    for i in side:
        f.write(i + '\n')

    f.close()


def setup():
    global AI1Deck, AI2Deck, isTraining, totalGames

    if reset:
        if isTraining:
            resetDB()
        # shuffle_deck(deck1)
        src_dir = os.getcwd() + '/WindBot-Ignite-master/bin/debug/Decks/' + deck1
        dst_dir = os.getcwd() + '/WindBot-Ignite-master/bin/debug/Decks/' + deck2
        shutil.copy(src_dir, dst_dir)

    resetYgoPro()

    # if not isTraining or True:
    AI2Deck = AIMaster


def main_game_runner(isTraining, totalGames, Id1, Id2):
    start = time.time()

    file_path = os.getcwd() + "/edopro_bin/ygopro.exe"

    if platform == "linux" or platform == "linux2":
        file_path = str(Path(__file__).resolve().parent.parent) + "/ProjectIgnisLinux/ygopro"

    g = subprocess.Popen([file_path], stdout=subprocess.DEVNULL)

    while (g.poll() == None and not isrespondingPID(g.pid)):
        time.sleep(1)

    time.sleep(5)

    print("	runningAi1 " + str(Id1))
    p1 = runAi(Deck=AI1Deck,
               Name=AI1Deck,
               Hand=2,
               TotalGames=totalGames,
               RolloutCount=rolloutCount,
               IsFirst=isFirst,
               IsTraining=isTraining,
               ShouldUpdate=isTraining,
               WinsThreshold=winThresh,
               PastWinsLimit=pastWinLim,
               Id=Id1
               )
    time.sleep(1)


    print("	runningAi2 " + str(Id2))
    p2 = runAi(Deck=AI2Deck,
               Name=AI2Deck,
               Hand=3,
               TotalGames=totalGames,
               RolloutCount=rolloutCount,
               IsFirst=(not isFirst),
               IsTraining=isTraining,
               ShouldUpdate=False,
               WinsThreshold=winThresh,
               PastWinsLimit=pastWinLim,
               Id=Id2
               )

    if (p1.poll() == None or p2.poll() == None):
        time.sleep(1)

    if (not (p1.poll() == None or p2.poll() == None)):
        print("	WARNING! AI is not running")

    timeout = 60
    AIstarttime = time.time()

    while (p1.poll() == None and p2.poll() == None):
        time.sleep(1)
        current_time = time.time()
        if current_time - AIstarttime > timeout:
            break
        continue

    if platform == "linux" or platform == "linux2":
        os.system("kill -9 " + str(g.pid))
    else:
        os.system("	TASKKILL /F /IM ygopro.exe")

    end = time.time()

    print("Time Past:" + str(datetime.timedelta(seconds=int(end - start))))
    print("Average Game Time:" + str(datetime.timedelta(seconds=int((end - start) / (totalGames)))))

def get_win(execution_id=0):
    win = 0

    conn = sqlite3.connect(os.getcwd() + '/cardData.cdb')
    c = conn.cursor()

    c.execute('SELECT DISTINCT GameId, Result FROM L_PlayRecord')
    records = c.fetchall()
    for record in records[execution_id:]:
        if record[1] == 1:
            win += 1

    conn.close()

    return win, len(records) - execution_id

def make_graph(list, title, xlabel, ylabel):
    x = range(len(list))
    fig, ax = plt.subplots()
    ax.plot(x, list)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()


def main():
    global reset, totalGames, generations
    parseArg()
    setup()

    allgame = 0
    winlog = []
    winratelog = []
    for g in range(generations):
        read_game_data.read_data()
        get_action_weights.load_data()
        proc = multiprocessing.Process(target=get_action_weights.run_server, args=())
        proc.start()

        for i in range(1):
            print("generation " + str(g) + " running game " + str(i))
            main_game_runner(True, totalGames, i * 2, i * 2 + 1)

        proc.terminate()  # sends a SIGTERM
        print("done cycle")
        win, game = get_win(allgame)
        if game == 0:
            print("No game recorded")
            continue
        allgame += game
        print("Win:" + str(win) + " Game:" + str(game) + " Win Rate:" + str(win / game * 100) + "%")
        winlog.append(win)
        winratelog.append(win / game * 100)
    make_graph(winlog, "Win", "Generation", "")
    make_graph(winratelog, "Win Rate", "Generation", "")
    read_game_data.read_data()

if __name__ == "__main__":
    main()
