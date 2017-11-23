#!/usr/bin/perl


use strict;
use warnings;

#Get the version the system is currently using.
my $kernel = `uname -r`;
chomp($kernel);

#Get the parameters passed to the kernel during boot.
my $cmdline = `cat /proc/cmdline`;
chomp($cmdline);

#Remove extra spaces.
$cmdline =~ s/\s+/ /g;

print $cmdline."\n";

my $device = `cat /boot/grub/device.map|egrep -o '\\(.*\\)'`;
chomp($device);

#Create the root line for the bootloader.
my $root = substr($device, 0, (length($device) - 1)).',0)';

#Create the image line for the bootloader.
my $image = 'kernel /vmlinuz-'.$kernel.' '.$cmdline." showopts";

#Create the failsafe image line for the bootloader.
my $imageFailsafe = $cmdline;

#Remove swap partition information and add failsafe parameters.
$imageFailsafe =~ s/\s{1}resume\s*=\s*\S+//;
$imageFailsafe =~ s/processor.max_cstate\s*=\s*0/processor.max_cstate=1/;
$imageFailsafe = $imageFailsafe." ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off nomodeset x11failsafe showopts";

#Create the initrd line for the bootloader.
my $initrd = 'initrd /initrd-'.$kernel;

my $bootloader = '/tmp/bootloader';

open(my $fh, '>', $bootloader) or die "Could not open file '$bootloader' $!";

print $fh "#Bootloader created from kernel security bundle install.\n";
print $fh "timeout 15\n";
print $fh "gfxmenu ".$root."/boot/message\n";
print $fh "\n\n";

print $fh "title Linux kernel ".$kernel."\n";
print $fh "\troot ".$root."\n";
print $fh "\t".$image."\n";
print $fh "\t".$initrd."\n";
print $fh "\n";

print $fh "title Linux Failsafe kernel ".$kernel."\n";
print $fh "\troot ".$root."\n";
print $fh "\t".$imageFailsafe."\n";
print $fh "\t".$initrd."\n";

close($fh);
