#!/bin/bash

#shuf -i 0-1000 -n 10 ( generate and display 10 random numbers between 0-1000)
#for i in `seq 10` ; do echo $i ; done
#for i in {5..10..5} ; do echo $i ; done
random=$$ # to generate Random numbers 


echo -n " Enter  Numbers to be sorted 
"
read n

echo -n " Read the numbers"

for (( i=0 ; i < $n ; i++ ))
do 
	read no[$i]
done 
echo -n " Unsorted Numbers"

for (( i=0 ; i < $n ; i++ ))
do 
	echo ${no[$i]}
done

#Sorting Operation 

for (( i = 0 ; i < $n ; i++ ))
do 
	for (( j=0 ; j < $n ; j++ ))
	do 
		if [ ${no[$i]} -gt ${no[$j]} ]
			t= ${no[$i]}
			no[$i]=${no[$j]}
			no[$j]=$t
		fi
		
	done
done

echo -n " Sorted Numbers"

for (( i = 0 ; i < $n ; i++ ))
do
		echo ${no[$i]}
		
done



		

