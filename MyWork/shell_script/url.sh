#!/bin/bash


getdomain()
{
   url=$1
   url_without_proto=${url#*://}
   echo "$url becomes $url_without_proto"
   
   domain_and_port=${url_without_proto%%/*}
   echo "$url_without_proto becomes $domain_and_port"

   domain=${domain_and_port%:*}
   echo "$domain_and_port becomes $domain"
   getent hosts $domain | head -1


}	

for url in $*
do 
	getdomain $url
done
