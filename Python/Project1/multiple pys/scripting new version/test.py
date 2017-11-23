#!/usr/bin/python


from initialize import Initialize
import os


csurBaseDir = '/hp/support/csur'
loggerName = 'csurLogger'

initialize = Initialize()

csurResourceDict = initialize.init(csurBaseDir, loggerName)

