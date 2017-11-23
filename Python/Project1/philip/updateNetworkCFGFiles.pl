#!/usr/bin/perl

use strict;


my %nicHash = ( em49 => 'em0',
                em50 => 'em1',
                em51 => 'em2',
                em52 => 'em3'
             );

my $nicFile = '';
my $newNicName = '';
my $cmd = '';

chdir "/etc/sysconfig/network";

my @ifcfgFiles=`ls ifcfg-bond*`;

foreach(@ifcfgFiles) {
        $nicFile = $_;
        chomp($nicFile);

        for my $key (keys %nicHash) {
                $cmd = "grep $key $nicFile > /dev/null 2>&1";
                if(system($cmd) == '0') {
                        $newNicName = $nicHash{$key};
                        system("cp $nicFile $nicFile'.bak'");
                        system("sed -i 's/$key/$newNicName/' $nicFile");
                        system("cp 'ifcfg-'$key 'ifcfg-'$newNicName");
                        system("rm 'ifcfg-'$key");
                }
        }
}
