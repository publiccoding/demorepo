# Embedded file name: ./cursesThread.py
from __future__ import division
from csurUpdateUtils import TimerThread
from math import *
import time
import datetime
import curses
import threading
import os
import logging
import textwrap
import re

class CursesThread(threading.Thread):

    def __init__(self, sessionScreenLog, cursesLog):
        super(CursesThread, self).__init__()
        self.cursesLog = cursesLog
        self.stop = threading.Event()
        self.timerThreadList = []
        self.messagesList = []
        self.userInput = None
        self.gettingUserInput = False
        self.userInputReady = False
        self.insertingUserInput = False
        self.lastMessageInMessagesList = None
        self.password = None
        self.gettingPassword = False
        self.stdscr = None
        sessionScreenHandler = logging.FileHandler(sessionScreenLog)
        self.sessionScreenLogger = logging.getLogger('sessionScreenLogger')
        self.sessionScreenLogger.setLevel(logging.INFO)
        self.sessionScreenLogger.addHandler(sessionScreenHandler)
        return

    def run(self):
        cursesLogFile = self.cursesLog
        cursesHandler = logging.FileHandler(cursesLogFile)
        logger = logging.getLogger('cursesLogFile')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        cursesHandler.setFormatter(formatter)
        logger.addHandler(cursesHandler)
        try:
            self.stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self.stdscr.nodelay(1)
            self.stdscr.keypad(1)
            curses.start_color()
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_GREEN)
            curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_RED)
            curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)
            curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
            feedbackHighlight = curses.color_pair(1)
            errorHighlight = curses.color_pair(2)
            informativeHighlight = curses.color_pair(3)
            scrollBarBackground = curses.color_pair(4)
            scrollBarHighlight = curses.color_pair(5)
            warnHighlight = curses.color_pair(6)
            finalHighlight = curses.color_pair(7)
            errorFeedbackHighlight = curses.color_pair(8)
            informativeFeedbackHighlight = curses.color_pair(9)
            finalFeedbackHighlight = curses.color_pair(10)
            maxRowsFeedbackWindow = 3
            windowFocus = 'conversationWindow'
            if len(self.messagesList) > 0:
                conversationHighlightPosition = len(self.messagesList) - 1
            else:
                conversationHighlightPosition = 0
            if len(self.timerThreadList) > 0:
                feedbackHighlightPosition = len(self.timerThreadList) - 1
            else:
                feedbackHighlightPosition = 0
            loopStarted = False
            yPosition = None
            previousMessagesListLength = 0
            previousTimerThreadListLength = 0
            wrappedMessagesList = []
            while not self.stop.isSet():
                time.sleep(0.04)
                initializing = False
                try:
                    y, x = self.stdscr.getmaxyx()
                    maxRowsConversationWindow = y - (3 + maxRowsFeedbackWindow)
                    if not loopStarted:
                        loopStarted = True
                        initializing = True
                        if len(self.messagesList) < maxRowsConversationWindow:
                            conversationStartingPosition = 0
                        else:
                            conversationStartingPosition = len(self.messagesList) - maxRowsConversationWindow
                        if len(self.timerThreadList) < maxRowsFeedbackWindow:
                            feedbackStartingPosition = 0
                        else:
                            feedbackStartingPosition = len(self.timerThreadList) - maxRowsFeedbackWindow
                    mainWindow = curses.newpad(y, x)
                    feedbackWindow = mainWindow.subpad(maxRowsFeedbackWindow + 2, 0, 0, 0)
                    feedbackWindow.border('|', '|', '-', '-', '+', '+', '+', '+')
                    scrollBarWindow = mainWindow.subpad(y - 4, 3, 4, 0)
                    scrollBarWindow.border('|', '|', '-', '-', '+', '+', '+', '+')
                    conversationWindow = mainWindow.subpad(y - 4, 0, 4, 2)
                    conversationWindow.border('|', '|', '-', '-', '+', '+', '+', '+')
                    input = self.stdscr.getch()
                    if input == curses.KEY_DOWN:
                        if windowFocus == 'conversationWindow':
                            if conversationHighlightPosition == maxRowsConversationWindow - 1 and conversationStartingPosition + maxRowsConversationWindow < len(self.messagesList):
                                conversationStartingPosition += 1
                            elif conversationHighlightPosition < maxRowsConversationWindow - 1 and conversationHighlightPosition < len(wrappedMessagesList) - 1:
                                conversationHighlightPosition += 1
                            else:
                                continue
                        elif feedbackHighlightPosition == maxRowsFeedbackWindow - 1 and feedbackStartingPosition + maxRowsFeedbackWindow < len(self.timerThreadList):
                            feedbackStartingPosition += 1
                        elif feedbackHighlightPosition < maxRowsFeedbackWindow - 1 and feedbackHighlightPosition < len(self.timerThreadList) - 1:
                            feedbackHighlightPosition += 1
                        else:
                            continue
                    elif input == curses.KEY_UP:
                        if windowFocus == 'conversationWindow':
                            if conversationHighlightPosition == 0 and conversationStartingPosition > 0:
                                conversationStartingPosition -= 1
                            elif conversationHighlightPosition == 0:
                                continue
                            else:
                                conversationHighlightPosition -= 1
                        elif feedbackHighlightPosition == 0 and feedbackStartingPosition > 0:
                            feedbackStartingPosition -= 1
                        elif feedbackHighlightPosition == 0:
                            continue
                        else:
                            feedbackHighlightPosition -= 1
                    elif input == 9:
                        if windowFocus == 'feedbackWindow':
                            windowFocus = 'conversationWindow'
                        else:
                            windowFocus = 'feedbackWindow'
                    if windowFocus == 'conversationWindow':
                        if self.gettingUserInput:
                            if input != -1:
                                if input == 263:
                                    if self.gettingPassword:
                                        self.password = self.password[:-1]
                                    else:
                                        self.userInput = self.userInput[:-1]
                                        self.insertUserInput()
                                elif input != 10 and not input < 32 and not input > 127:
                                    if maxRowsConversationWindow < len(self.messagesList):
                                        if conversationStartingPosition != len(self.messagesList) - maxRowsConversationWindow:
                                            conversationStartingPosition = len(self.messagesList) - maxRowsConversationWindow
                                            conversationHighlightPosition = maxRowsConversationWindow - 1
                                        else:
                                            conversationHighlightPosition = maxRowsConversationWindow - 1
                                    elif conversationHighlightPosition != len(self.messagesList) - 1:
                                        conversationHighlightPosition = len(self.messagesList) - 1
                                    if self.gettingPassword:
                                        self.password += chr(input)
                                    else:
                                        self.userInput += chr(input)
                                        self.insertUserInput()
                                elif input == 10:
                                    self.gettingUserInput = False
                                    self.userInputReady = True
                                    if self.gettingPassword:
                                        self.gettingPassword = False
                                    else:
                                        self.recordScreenConversation(self.messagesList[-1][1])
                    if yPosition != None and maxRowsConversationWindow > yPosition:
                        if conversationStartingPosition - (maxRowsConversationWindow - yPosition) >= 0:
                            conversationStartingPosition = conversationStartingPosition - (maxRowsConversationWindow - yPosition + 1)
                        else:
                            conversationStartingPosition = 0
                    if conversationHighlightPosition > maxRowsConversationWindow - 1:
                        conversationHighlightPosition = maxRowsConversationWindow - 1
                    if len(self.messagesList) != previousMessagesListLength:
                        previousMessagesListLength = len(self.messagesList)
                        if len(self.messagesList) > maxRowsConversationWindow:
                            conversationStartingPosition = len(self.messagesList) - maxRowsConversationWindow
                            conversationHighlightPosition = maxRowsConversationWindow - 1
                        else:
                            conversationHighlightPosition = len(self.messagesList) - 1
                    if len(self.timerThreadList) != previousTimerThreadListLength:
                        previousTimerThreadListLength = len(self.timerThreadList)
                        if len(self.timerThreadList) > maxRowsFeedbackWindow:
                            feedbackStartingPosition = len(self.timerThreadList) - maxRowsFeedbackWindow
                            feedbackHighlightPosition = maxRowsFeedbackWindow - 1
                        else:
                            feedbackHighlightPosition = len(self.timerThreadList) - 1
                    yPosition = 1
                    if windowFocus == 'feedbackWindow':
                        feedbackWindow.attrset(curses.A_BOLD)
                        conversationWindow.attrset(curses.A_DIM)
                        scrollBarWindow.attrset(curses.A_DIM)
                    else:
                        feedbackWindow.attrset(curses.A_DIM)
                        conversationWindow.attrset(curses.A_BOLD)
                        scrollBarWindow.attrset(curses.A_BOLD)
                    if len(self.timerThreadList) > 0:
                        for i in range(feedbackStartingPosition, feedbackStartingPosition + maxRowsFeedbackWindow):
                            timerList = self.timerThreadList[i]
                            if timerList[1].isAlive():
                                message = timerList[1].getMessage() + timerList[1].getTimeStamp()
                            else:
                                message = timerList[0]
                            if i == feedbackHighlightPosition:
                                feedbackWindow.addstr(yPosition, 1, message, feedbackHighlight)
                            else:
                                feedbackWindow.addstr(yPosition, 1, message)
                            yPosition += 1
                            if i == len(self.timerThreadList) - 1:
                                break

                    yPosition = 1
                    if len(self.messagesList) > 0:
                        wrappedMessagesList = self.__wrapText(self.messagesList[conversationStartingPosition:conversationStartingPosition + maxRowsConversationWindow], maxRowsConversationWindow, x - 5)
                        for i in range(0, maxRowsConversationWindow):
                            messageList = wrappedMessagesList[i]
                            message = messageList[1]
                            if messageList[0] == 'error':
                                if i == conversationHighlightPosition:
                                    conversationWindow.addstr(yPosition, 1, message, errorFeedbackHighlight)
                                else:
                                    conversationWindow.addstr(yPosition, 1, message, errorHighlight)
                            elif messageList[0] == 'informative':
                                if i == conversationHighlightPosition:
                                    conversationWindow.addstr(yPosition, 1, message, informativeFeedbackHighlight)
                                else:
                                    conversationWindow.addstr(yPosition, 1, message, informativeHighlight)
                            elif messageList[0] == 'warning':
                                if i == conversationHighlightPosition:
                                    conversationWindow.addstr(yPosition, 1, message, feedbackHighlight)
                                else:
                                    conversationWindow.addstr(yPosition, 1, message, warnHighlight)
                            elif messageList[0] == 'final':
                                if i == conversationHighlightPosition:
                                    conversationWindow.addstr(yPosition, 1, message, finalFeedbackHighlight)
                                else:
                                    conversationWindow.addstr(yPosition, 1, message, finalHighlight)
                            elif i == conversationHighlightPosition:
                                conversationWindow.addstr(yPosition, 1, message, feedbackHighlight)
                            else:
                                conversationWindow.addstr(yPosition, 1, message)
                            if i == maxRowsConversationWindow - 1 and conversationHighlightPosition > i:
                                scrollBarWindow.addstr(maxRowsConversationWindow, 1, ' ', scrollBarHighlight)
                            elif i == conversationHighlightPosition:
                                scrollBarWindow.addstr(yPosition, 1, ' ', scrollBarHighlight)
                            else:
                                scrollBarWindow.addstr(yPosition, 1, ' ', scrollBarBackground)
                            yPosition += 1
                            if i == len(wrappedMessagesList) - 1:
                                if y >= len(wrappedMessagesList):
                                    for i in range(0, y - len(wrappedMessagesList) - 6):
                                        scrollBarWindow.addstr(yPosition, 1, ' ', scrollBarBackground)
                                        yPosition += 1

                                break

                    scrollBarWindow.refresh(0, 0, 4, 0, y, 3)
                    feedbackWindow.refresh(0, 0, 0, 0, 5, x)
                    conversationWindow.refresh(0, 0, 4, 2, y, x)
                except curses.error:
                    logger.exception('A curses exception occurred')
                    curses.endwin()

            curses.echo()
            curses.nocbreak()
            curses.endwin()
        except Exception as err:
            curses.echo()
            curses.nocbreak()
            curses.endwin()
            logger.exception('An exception occured while in curses mode.' + str(err))

        return

    def join(self, timeout = None):
        self.stop.set()
        super(CursesThread, self).join(timeout)

    def insertTimerThread(self, timerThread, *args):
        if len(args) == 0:
            self.timerThreadList.append(timerThread)
        else:
            self.timerThreadList[args[0]] = timerThread

    def getTimerThreadLocation(self):
        return len(self.timerThreadList) - 1

    def updateTimerThread(self, message, index):
        self.timerThreadList[index][0] = message

    def insertMessage(self, message):
        self.messagesList.append(message)
        self.recordScreenConversation(message[1])

    def insertUserInput(self):
        currentLine = self.lastMessageInMessagesList + self.userInput
        self.messagesList[-1][1] = currentLine

    def recordScreenConversation(self, message):
        self.sessionScreenLogger.info(message)

    def getUserInput(self, prompt, *args):
        if len(args) == 1:
            self.gettingPassword = True
            self.password = ''
        self.lastMessageInMessagesList = prompt[1]
        self.messagesList.append(prompt)
        self.userInputReady = False
        self.gettingUserInput = True
        self.userInput = ''

    def isUserInputReady(self):
        return self.userInputReady

    def getUserResponse(self):
        return self.userInput

    def getUserPassword(self):
        return self.password

    def __wrapText(self, messagesList, maxRowsConversationWindow, width):
        wrappedMessagesList = []
        for message in messagesList:
            messageType = message[0]
            if len(message[1].rstrip()) != 0:
                wrappedTextList = textwrap.wrap(message[1], width)
                for line in wrappedTextList:
                    wrappedMessagesList.append([messageType, line])

            else:
                wrappedMessagesList.append(message)

        if len(wrappedMessagesList) > maxRowsConversationWindow:
            return wrappedMessagesList[len(wrappedMessagesList) - maxRowsConversationWindow:maxRowsConversationWindow + 1]
        else:
            return wrappedMessagesList