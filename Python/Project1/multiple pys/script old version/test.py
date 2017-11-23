#!/usr/bin/python


import re


with open('/boot/efi/EFI/SuSE/elilo.conf') as f:
	for line in f:
		if 'image' in line:
			kernel = (re.sub(' +', ' ', line)).strip()
		elif 'initrd' in line:
			initrd = (re.sub(' +', ' ', line)).strip()
		elif 'root' in line and not 'append' in line:
			root = (re.sub(' +', ' ', line)).strip()
		elif 'append' in line:
			print line

