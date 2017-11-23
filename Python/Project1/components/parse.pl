#!/usr/bin/perl


use strict;
use warnings;


my @automationRPMArray;

open(my $fh, "<", "rpmListSortedNew") or die "Failed to open file: $!\n";

while(<$fh>) { 
	chomp; 
	push @automationRPMArray, $_;
} 

close $fh;


open(my $fh2, "<", $ARGV[0]) or die "Failed to open file: $!\n";

open(my $fh3, ">", 'result') or die "Failed to open file: $!\n";

my $status = "";

while(<$fh2>) { 
	chomp; 
	my $status = 'notFound';

	foreach my $rpm (@automationRPMArray) {
		if($_ =~ /$rpm/) {
			 $status = 'found';
		}
	}

	if($status eq 'notFound') {
		print $fh3 $_."\n";
	}
} 

close $fh2;
close $fh3;
