#!/usr/bin/perl


use strict;
use warnings;

#Get new kernel version that the system is being updated to.
my ($newKernel) = @ARGV;

#Get the version the system is currently using.
my $oldKernel = `uname -r`;
chomp($oldKernel);

#Get the parameters passed to the kernel during boot.
my $cmdline = `cat /proc/cmdline`;
chomp($cmdline);

#Remove extra spaces.
$cmdline =~ s/\s+/ /g;

#Get system information so that the correct bootloader function is called.
my $system = `dmidecode -s system-product-name|awk '{print \$2\$3}'`;

if ($system =~ /G7/) {
	legacySystem($newKernel, $oldKernel, $cmdline);
} else {
	uefiSystem($newKernel, $oldKernel, $cmdline);
}

#This function is for legacy systems whose bootloader is menu.lst.
sub legacySystem {
	my ($newKernel, $oldKernel, $cmdline) = @_;
	my $device = `cat /boot/grub/device.map|egrep -o '\\(.*\\)'`;
	chomp($device);

	#Create the root line for the bootloader.
	my $root = substr($device, 0, (length($device) - 1)).',0)';

	#Create the image line for the bootloader.
	my $oldImage = 'kernel /vmlinuz-'.$oldKernel.' '.$cmdline." showopts";
	my $newImage = 'kernel /vmlinuz-'.$newKernel.' '.$cmdline." showopts";

	#Create the failsafe image line for the bootloader.
	my $imageFailsafe = $cmdline;

	#Remove swap partition information and add failsafe parameters.
	$imageFailsafe =~ s/\s{1}resume\s*=\s*\S+//;
	$imageFailsafe =~ s/processor.max_cstate\s*=\s*0/processor.max_cstate=1/;
	$imageFailsafe = $imageFailsafe." ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off nomodeset x11failsafe showopts";
	my $oldImageFailsafe = 'kernel /vmlinuz-'.$oldKernel.' '.$imageFailsafe;
	my $newImageFailsafe = 'kernel /vmlinuz-'.$newKernel.' '.$imageFailsafe;

	#Create the initrd line for the bootloader.
	my $oldInitrd = 'initrd /initrd-'.$oldKernel;
	my $newInitrd = 'initrd /initrd-'.$newKernel;

	createLegacyBootloader($root, $newKernel, $newImage, $newInitrd, $newImageFailsafe, $oldKernel, $oldImage, $oldInitrd, $oldImageFailsafe);
}

#This function creates an updated menu.lst for legacy systems.
sub createLegacyBootloader {
	my (@parameters) = @_;
	my $offset = 0;
	my $bootloader = '/tmp/bootloader';

	open(my $fh, '>', $bootloader) or die "Could not open file '$bootloader' $!";

	print $fh "#Bootloader created from kernel security bundle install.\n";
	print $fh "timeout 15\n";
	print $fh "gfxmenu ".$parameters[0]."/boot/message\n";
	print $fh "\n\n";

	for(my $i = 0; $i < 2; $i++) { 
		if($i != 0) {
			$offset = 4; 
			print $fh "\n\n\n";
		}
		
		print $fh "title Linux kernel ".$parameters[1+$offset]."\n";
		print $fh "\troot ".$parameters[0]."\n";
		print $fh "\t".$parameters[2+$offset]."\n";
		print $fh "\t".$parameters[3+$offset]."\n";
		print $fh "\n";

		print $fh "title Linux Failsafe kernel ".$parameters[1+$offset]."\n";
		print $fh "\troot ".$parameters[0]."\n";
		print $fh "\t".$parameters[4+$offset]."\n";
		print $fh "\t".$parameters[3+$offset]."\n";
	}

	close($fh);

	#Put the updated bootloader in place.
	my $date = `date +%j%b%Y`;
	`cp /boot/grub/menu.lst /boot/grub/menu.lst.BAK_$date`;
	`mv $bootloader /boot/grub/menu.lst`;
}

#This function is for UEFI systems whose bootloader is elilo.conf.
sub uefiSystem {
	my ($newKernel, $oldKernel, $cmdline) = @_;

	#Create the append line for the bootloader.
	my ($append) = $cmdline =~ /(root\s*=\s*\/dev.*)$/;
	my $appendNonFailsafe = 'append = "'.$append.'"';

	#Create the failsafe append line for the bootloader.
	my $appendFailsafe = 'append = "ide=nodma apm=off noresume edd=off powersaved=off nohz=off highres=off processsor.max+cstate=1 nomodeset x11failsafe '.$append.'"';

	#Create the root line for the bootloader.
	my ($root) = $cmdline =~ /root\s*=\s*(\/dev\S+).*$/;
	$root = 'root = '.$root;

	#Create the image line for the bootloader.
	my $oldImage = 'image = /boot/vmlinuz-'.$oldKernel;
	my $newImage = 'image = /boot/vmlinuz-'.$newKernel;

	#Create the initrd line for the bootloader.
	my $oldInitrd = 'initrd = /boot/initrd-'.$oldKernel;
	my $newInitrd = 'initrd = /boot/initrd-'.$newKernel;

	createUefiBootloader($root, $appendNonFailsafe, $appendFailsafe, $newKernel, $newImage, $newInitrd, $oldKernel, $oldImage, $oldInitrd);
}

#This function creates an updated elilo.conf for legacy systems.
sub createUefiBootloader {
	my (@parameters) = @_;
	my $offset = 0;
	my $label = 'One';

	my $bootloader = '/tmp/bootloader';

	open(my $fh, '>', $bootloader) or die "Could not open file '$bootloader' $!";

	print $fh "#Bootloader created from kernel security bundle install.\n";
	print $fh "timeout = 150\n";
	print $fh "secure-boot = on\n";
	print $fh "prompt\n";
	print $fh "\n\n";

	for(my $i = 0; $i < 2; $i++) { 
		if($i != 0) {
			$offset = 3; 
			$label = 'Two';
			print $fh "\n\n\n";
		}

		print $fh $parameters[4+$offset]."\n";
		print $fh "\tdescription = \"Linux kernel ".$parameters[3+$offset]."\"\n";
		print $fh "\tlabel = Linux".$label."\n";
		print $fh "\t".$parameters[5+$offset]."\n";
		print $fh "\t".$parameters[1]."\n";
		print $fh "\t".$parameters[0]."\n";
		print $fh "\n";

		print $fh $parameters[4+$offset]."\n";
		print $fh "\tdescription = \"Linux Failsafe kernel ".$parameters[3+$offset]."\"\n";
		print $fh "\tlabel = Failsafe".$label."\n";
		print $fh "\t".$parameters[5+$offset]."\n";
		print $fh "\t".$parameters[2]."\n";
		print $fh "\t".$parameters[0]."\n";
	}

	close($fh);

	#Put the updated bootloader in place.
	my $date = `date +%j%b%Y`;
	`cp /etc/elilo.conf /etc/elilo.conf.BAK_$date`;
	`mv $bootloader /etc/elilo.conf`;
	`/sbin/elilo`;
}
