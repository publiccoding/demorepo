#!/bin/bash

ping 10.154.44.25 > /dev/null 2>&1 & 
ping 10.154.44.24 > /dev/null 2>&1 & 
ping 10.154.44.22 > /dev/null 2>&1 & 

sleep 90
